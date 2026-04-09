"""Agent harness: runs engineer then scientist in a local directory."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import anthropic

from agents.engineer import build_engineer_prompt, format_engineer_context
from agents.scientist import build_scientist_prompt, format_scientist_context
from agents.tools import collect_tool_schemas
from agents.tools import bash, edit, read, search, web_fetch, timer, create_stream
from shared.config import ANTHROPIC_MODEL, AWS_REGION
from shared.protocol import now_iso


def _make_client() -> anthropic.AsyncAnthropicBedrock:
    return anthropic.AsyncAnthropicBedrock(aws_region=AWS_REGION)


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------

class AgentTimer:
    def __init__(self, timeout_seconds: int, work_dir: str):
        self.timeout = timeout_seconds
        self.work_dir = work_dir
        self.start_time: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def expired(self) -> bool:
        if not self.start_time:
            return False
        return time.time() - self.start_time >= self.timeout

    def remaining(self) -> int:
        if not self.start_time:
            return self.timeout
        return max(0, self.timeout - int(time.time() - self.start_time))

    def start(self):
        self.start_time = time.time()
        self._thread = threading.Thread(target=self._tick, daemon=True)
        self._thread.start()

    def _tick(self):
        path = os.path.join(self.work_dir, ".remaining_seconds")
        while not self._stop.is_set():
            with open(path, "w") as f:
                f.write(str(self.remaining()))
            if self.remaining() <= 0:
                break
            self._stop.wait(30)

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------------------
# Stream watcher — tails JSONL files, broadcasts via ws_manager
# ---------------------------------------------------------------------------

class StreamWatcher:
    def __init__(self, streams_dir: str, run_id: str, ws_manager):
        self.streams_dir = streams_dir
        self.run_id = run_id
        self.ws = ws_manager
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._offsets: dict[str, int] = {}
        self._seen_frames: dict[str, set[str]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self):
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def _watch_loop(self):
        while not self._stop.is_set():
            self._scan()
            self._stop.wait(0.5)

    def _scan(self):
        streams_dir = Path(self.streams_dir)
        if not streams_dir.exists():
            return

        for jsonl_file in streams_dir.glob("*.jsonl"):
            stream_id = jsonl_file.stem
            offset = self._offsets.get(str(jsonl_file), 0)
            try:
                with open(jsonl_file, "r") as f:
                    f.seek(offset)
                    new_lines = f.readlines()
                    new_offset = f.tell()
            except Exception:
                continue

            if new_lines:
                self._offsets[str(jsonl_file)] = new_offset
                points = []
                for line in new_lines:
                    line = line.strip()
                    if line:
                        try:
                            points.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                if points and self._loop and self.ws:
                    asyncio.run_coroutine_threadsafe(
                        self.ws.broadcast(self.run_id, {
                            "type": "stream_data",
                            "data": {"stream_id": stream_id, "points": points},
                        }),
                        self._loop,
                    )

        for entry in streams_dir.iterdir():
            if not entry.is_dir():
                continue
            stream_id = entry.name
            seen = self._seen_frames.setdefault(stream_id, set())
            frames = sorted(entry.glob("frame_*.png"))
            for frame_path in [f for f in frames if f.name not in seen]:
                seen.add(frame_path.name)
                try:
                    b64 = base64.b64encode(frame_path.read_bytes()).decode()
                except Exception:
                    continue
                if self._loop and self.ws:
                    asyncio.run_coroutine_threadsafe(
                        self.ws.broadcast(self.run_id, {
                            "type": "stream_data",
                            "data": {"stream_id": stream_id,
                                     "points": [{"frame": b64, "name": frame_path.name}]},
                        }),
                        self._loop,
                    )

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

async def execute_tool(name: str, input: dict, work_dir: str,
                       run_id: str = "", state=None, ws=None) -> str:
    if name == "bash":
        return await bash.execute(input, work_dir)
    elif name == "edit":
        return await edit.execute(input, work_dir)
    elif name == "read":
        return await read.execute(input, work_dir)
    elif name == "search":
        return await search.execute(input, work_dir)
    elif name == "web_fetch":
        return await web_fetch.execute(input, work_dir)
    elif name == "check_timer":
        return await timer.execute(input, work_dir)
    elif name == "create_stream":
        return await create_stream.execute(input, work_dir, run_id=run_id,
                                           state=state, ws=ws)
    else:
        return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------

def serialize_content(content) -> Any:
    if isinstance(content, str):
        return content
    result = []
    for block in content:
        if hasattr(block, "model_dump"):
            result.append(block.model_dump())
        elif isinstance(block, dict):
            result.append(block)
        else:
            result.append({"type": "text", "text": str(block)})
    return result


def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
    return "\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------

async def run_agent(
    agent_id: str,
    system_prompt: str,
    initial_context: str,
    timeout_seconds: int,
    work_dir: str,
    run_id: str = "",
    state=None,
    ws=None,
) -> str:
    """Run one agent phase. Returns the agent's final text output."""
    client = _make_client()
    tools = collect_tool_schemas()
    agent_timer = AgentTimer(timeout_seconds, work_dir)
    agent_timer.start()

    messages: list[dict[str, Any]] = [{"role": "user", "content": initial_context}]
    tool_call_count = 0
    total_tokens = 0

    try:
        while not agent_timer.expired:
            try:
                response = await client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )
            except Exception as api_err:
                print(f"[agent {agent_id}] API error: {api_err}")
                # Retry once after a brief pause
                import asyncio as _aio
                await _aio.sleep(2)
                response = await client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens
            messages.append({"role": "assistant", "content": response.content})

            # Update agent state
            if state and agent_id:
                await state.update_agent(agent_id,
                    tool_calls=tool_call_count,
                    tokens_used=total_tokens,
                    last_heartbeat=now_iso())

            # Transcript
            if state and agent_id:
                from shared.protocol import TranscriptMessage
                await state.append_transcript(agent_id, [
                    TranscriptMessage(role="assistant",
                                     content=serialize_content(response.content)),
                ])
                if ws:
                    await ws.broadcast(run_id, {
                        "type": "transcript",
                        "data": {"agent_id": agent_id, "messages": [
                            {"role": "assistant",
                             "content": str(serialize_content(response.content))[:2000]}
                        ]},
                    })

            if response.stop_reason != "tool_use":
                return extract_text(response.content)

            # Execute tools
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_call_count += 1

                if block.name == "signal_done":
                    return block.input.get("result", "")

                # Update activity
                if state and agent_id:
                    await state.update_agent(agent_id,
                        last_activity=f"{block.name}: {str(block.input)[:50]}",
                        tool_calls=tool_call_count)

                result_str = await execute_tool(
                    block.name, block.input, work_dir,
                    run_id=run_id, state=state, ws=ws,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            messages.append({"role": "user", "content": tool_results})

        return "TIMEOUT: Ran out of time."

    finally:
        agent_timer.stop()


# ---------------------------------------------------------------------------
# Run both phases: engineer → scientist
# ---------------------------------------------------------------------------

async def run_both_phases(
    run_id: str,
    sim_spec: dict,
    research_traces: list,
    engineer_timeout: int,
    scientist_timeout: int,
    state,
    ws,
) -> None:
    """Run engineer then scientist in /lab/{run_id}/. Called as asyncio task."""
    work_dir = os.path.join("lab", run_id)
    streams_dir = os.path.join(work_dir, "streams")
    os.makedirs(streams_dir, exist_ok=True)

    eng_id = f"{run_id}-eng"
    sci_id = f"{run_id}-sci"

    # Start stream watcher
    watcher = StreamWatcher(streams_dir, run_id, ws)
    watcher.start()

    try:
        # --- ENGINEER ---
        await state.update_agent(eng_id, status="running", started_at=now_iso())
        await ws.broadcast(run_id, {"type": "phase_change", "data": {"status": "engineering"}})

        engineer_result = await run_agent(
            agent_id=eng_id,
            system_prompt=build_engineer_prompt(sim_spec),
            initial_context=format_engineer_context(sim_spec, research_traces),
            timeout_seconds=engineer_timeout,
            work_dir=work_dir,
            run_id=run_id, state=state, ws=ws,
        )

        await state.update_agent(eng_id, status="done", result=engineer_result)
        Path(os.path.join(work_dir, "handoff.md")).write_text(engineer_result)

        # --- SCIENTIST ---
        await state.update_agent(sci_id, status="running", started_at=now_iso())
        await state.update_run(run_id, status="science")
        await ws.broadcast(run_id, {"type": "phase_change", "data": {"status": "science"}})

        scientist_result = await run_agent(
            agent_id=sci_id,
            system_prompt=build_scientist_prompt(sim_spec),
            initial_context=format_scientist_context(sim_spec, research_traces, engineer_result),
            timeout_seconds=scientist_timeout,
            work_dir=work_dir,
            run_id=run_id, state=state, ws=ws,
        )

        await state.update_agent(sci_id, status="done", result=scientist_result)
        await state.update_run(run_id, status="complete", findings=scientist_result)
        await ws.broadcast(run_id, {"type": "complete", "data": {"findings": scientist_result}})

    except Exception as e:
        import traceback
        err = f"{type(e).__name__}: {e}"
        print(f"[harness] Run {run_id} failed: {err}")
        traceback.print_exc()
        await state.update_run(run_id, status="failed", error=err)
        await ws.broadcast(run_id, {"type": "error", "data": {"error": err}})
    finally:
        watcher.stop()
