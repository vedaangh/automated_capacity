"""Agent harness: runs engineer then scientist sequentially on the same EC2 instance."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import anthropic

from agents.engineer import build_engineer_prompt, format_engineer_context
from agents.scientist import build_scientist_prompt, format_scientist_context
from agents.server_client import ServerClient
from agents.tools import collect_tool_schemas
from agents.tools import bash, edit, read, search, web_fetch, timer, create_stream
from shared.config import ANTHROPIC_MODEL, AWS_REGION
from shared.protocol import now_iso


def _make_client() -> anthropic.AsyncAnthropicBedrock:
    """Create a Bedrock client. Auth via AWS credentials (env vars or IAM role)."""
    return anthropic.AsyncAnthropicBedrock(aws_region=AWS_REGION)


# ---------------------------------------------------------------------------
# Timer: background thread writes .remaining_seconds every 30s
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
# HeartbeatTask: async task POSTs progress every N seconds
# ---------------------------------------------------------------------------

class HeartbeatTask:
    def __init__(self, server: ServerClient, agent_id: str, interval: int = 30):
        self.server = server
        self.agent_id = agent_id
        self.interval = interval
        self._task: asyncio.Task | None = None
        self.tool_calls = 0
        self.tokens = 0
        self.last_activity = ""

    def start(self):
        self._task = asyncio.create_task(self._loop())

    async def _loop(self):
        while True:
            try:
                await self.server.heartbeat(
                    self.agent_id, self.tool_calls,
                    self.tokens, self.last_activity,
                )
            except Exception:
                pass
            await asyncio.sleep(self.interval)

    def stop(self):
        if self._task:
            self._task.cancel()


# ---------------------------------------------------------------------------
# StreamWatcher: daemon thread tails /lab/streams/*.jsonl and POSTs to server
# ---------------------------------------------------------------------------

class StreamWatcher:
    def __init__(self, streams_dir: str, server: ServerClient,
                 run_id: str, poll_interval: float = 0.5):
        self.streams_dir = streams_dir
        self.server = server
        self.run_id = run_id
        self.poll_interval = poll_interval
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
            self._stop.wait(self.poll_interval)

    def _scan(self):
        streams_dir = Path(self.streams_dir)
        if not streams_dir.exists():
            return

        # JSONL files
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
                if points and self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self.server.push_stream_data(self.run_id, stream_id, points),
                        self._loop,
                    )

        # Video stream directories
        for entry in streams_dir.iterdir():
            if not entry.is_dir():
                continue
            stream_id = entry.name
            seen = self._seen_frames.setdefault(stream_id, set())
            frames = sorted(entry.glob("frame_*.png"))
            new_frames = [f for f in frames if f.name not in seen]
            for frame_path in new_frames:
                seen.add(frame_path.name)
                try:
                    b64 = base64.b64encode(frame_path.read_bytes()).decode()
                except Exception:
                    continue
                if self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self.server.push_stream_data(
                            self.run_id, stream_id,
                            [{"frame": b64, "name": frame_path.name}],
                        ),
                        self._loop,
                    )

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------

async def execute_tool(name: str, input: dict, work_dir: str,
                       server: ServerClient, run_id: str) -> str:
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
        return await create_stream.execute(input, work_dir, server=server, run_id=run_id)
    else:
        return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Helpers for serializing Claude API content blocks
# ---------------------------------------------------------------------------

def serialize_content(content) -> Any:
    """Convert Claude API content blocks to JSON-serializable form."""
    if isinstance(content, str):
        return content
    result = []
    for block in content:
        if hasattr(block, "model_dump"):
            result.append(block.model_dump())
        elif hasattr(block, "to_dict"):
            result.append(block.to_dict())
        elif isinstance(block, dict):
            result.append(block)
        else:
            result.append({"type": "text", "text": str(block)})
    return result


def extract_text(content) -> str:
    """Extract text from Claude API response content."""
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
    server: ServerClient,
    run_id: str,
    work_dir: str,
    heartbeat: HeartbeatTask | None = None,
) -> str:
    """Run one agent phase. Returns the agent's final text output."""
    client = _make_client()
    tools = collect_tool_schemas()
    agent_timer = AgentTimer(timeout_seconds, work_dir)
    agent_timer.start()

    messages: list[dict[str, Any]] = [{"role": "user", "content": initial_context}]

    try:
        while not agent_timer.expired:
            response = await client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
                tools=tools,
            )

            # Track usage
            usage_tokens = response.usage.input_tokens + response.usage.output_tokens
            if heartbeat:
                heartbeat.tokens += usage_tokens

            # Append assistant response
            messages.append({"role": "assistant", "content": response.content})

            # Stream transcript
            await server.append_transcript(agent_id, [
                {"role": "assistant", "content": serialize_content(response.content),
                 "ts": now_iso()},
            ])

            # Check stop reason
            if response.stop_reason != "tool_use":
                return extract_text(response.content)

            # Execute tool calls
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if heartbeat:
                    heartbeat.tool_calls += 1
                    heartbeat.last_activity = f"{block.name}: {str(block.input)[:50]}"

                # signal_done: exit immediately
                if block.name == "signal_done":
                    return block.input.get("result", "")

                result_str = await execute_tool(
                    block.name, block.input, work_dir, server, run_id,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            messages.append({"role": "user", "content": tool_results})

            # Stream transcript (tool results, truncated)
            await server.append_transcript(agent_id, [
                {"role": "tool_result", "tool_use_id": tr["tool_use_id"],
                 "content": tr["content"][:2000], "ts": now_iso()}
                for tr in tool_results
            ])

        # Timeout
        return "TIMEOUT: Ran out of time. Returning current state of work."

    finally:
        agent_timer.stop()


# ---------------------------------------------------------------------------
# Main: runs engineer then scientist
# ---------------------------------------------------------------------------

async def main(payload_path: str):
    payload = json.loads(Path(payload_path).read_text())

    server = ServerClient(payload["server_url"])
    run_id = payload["run_id"]
    work_dir = "/lab"
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(f"{work_dir}/streams", exist_ok=True)

    # Start stream watcher
    watcher = StreamWatcher(f"{work_dir}/streams", server, run_id)
    watcher.start()

    try:
        # ENGINEER PHASE
        eng_id = payload["engineer_agent_id"]
        eng_hb = HeartbeatTask(server, eng_id)
        eng_hb.start()

        engineer_result = await run_agent(
            agent_id=eng_id,
            system_prompt=build_engineer_prompt(payload["sim_spec"]),
            initial_context=format_engineer_context(
                payload["sim_spec"], payload["research_traces"],
            ),
            timeout_seconds=payload["engineer_timeout"],
            server=server, run_id=run_id, work_dir=work_dir,
            heartbeat=eng_hb,
        )

        eng_hb.stop()
        await server.signal_done(eng_id, result=engineer_result, status="done")
        Path(f"{work_dir}/handoff.md").write_text(engineer_result)

        # SCIENTIST PHASE
        sci_id = payload["scientist_agent_id"]
        sci_hb = HeartbeatTask(server, sci_id)
        sci_hb.start()

        scientist_result = await run_agent(
            agent_id=sci_id,
            system_prompt=build_scientist_prompt(payload["sim_spec"]),
            initial_context=format_scientist_context(
                payload["sim_spec"], payload["research_traces"], engineer_result,
            ),
            timeout_seconds=payload["scientist_timeout"],
            server=server, run_id=run_id, work_dir=work_dir,
            heartbeat=sci_hb,
        )

        sci_hb.stop()
        await server.signal_done(sci_id, result=scientist_result, status="done")

    except Exception as e:
        # Try to report failure
        try:
            await server.signal_done(
                payload.get("engineer_agent_id", "unknown"),
                result=f"Harness crashed: {e}",
                status="failed",
            )
        except Exception:
            pass
        raise
    finally:
        watcher.stop()
        await server.close()


def self_terminate():
    """Terminate this EC2 instance."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://169.254.169.254/latest/meta-data/instance-id"],
            capture_output=True, text=True, timeout=5,
        )
        instance_id = result.stdout.strip()
        if instance_id.startswith("i-"):
            subprocess.run(
                ["aws", "ec2", "terminate-instances", "--instance-ids", instance_id],
                timeout=10,
            )
    except Exception:
        pass


# Entry point for running on EC2
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.payload))
    self_terminate()
