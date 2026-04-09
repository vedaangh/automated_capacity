"""Orchestrator: Claude tool-use loop that drives the research pipeline."""

from __future__ import annotations

import anthropic

from orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from orchestrator.tools import ORCHESTRATOR_TOOLS, execute_orchestrator_tool
from server.state import StateManager
from server.ws_manager import WSManager
from shared.config import AWS_REGION, ORCHESTRATOR_MODEL
from shared.protocol import TranscriptMessage, now_iso


def _serialize_content(content) -> list[dict]:
    """Convert Claude content blocks to JSON-serializable dicts."""
    result = []
    for block in content:
        if hasattr(block, "model_dump"):
            result.append(block.model_dump())
        elif isinstance(block, dict):
            result.append(block)
        else:
            result.append({"type": "text", "text": str(block)})
    return result


async def run_orchestrator(run_id: str, state: StateManager, ws: WSManager) -> None:
    """Main orchestrator loop. Runs as an asyncio task in the server process."""
    run = await state.get_run(run_id)
    if not run:
        return

    # Create an orchestrator agent record so transcripts are stored
    orch_id = f"{run_id}-orch"
    await state.create_agent(run_id, "orchestrator", timeout=0)
    await state.update_agent(orch_id, status="running", started_at=now_iso())

    client = anthropic.AsyncAnthropicBedrock(aws_region=AWS_REGION)
    messages = [{"role": "user", "content": f"Research question: {run.question}"}]

    turn = 0
    total_tokens = 0
    try:
        while True:
            turn += 1
            response = await client.messages.create(
                model=ORCHESTRATOR_MODEL,
                max_tokens=4096,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                messages=messages,
                tools=ORCHESTRATOR_TOOLS,
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens
            messages.append({"role": "assistant", "content": response.content})

            # Store + broadcast transcript
            serialized = _serialize_content(response.content)
            await state.append_transcript(orch_id, [
                TranscriptMessage(role="assistant", content=serialized),
            ])
            await state.update_agent(orch_id, tool_calls=turn,
                                     tokens_used=total_tokens,
                                     last_heartbeat=now_iso())

            # Build a readable summary for the WS broadcast
            text_parts = []
            tool_calls = []
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    text_parts.append(block.text)
                if block.type == "tool_use":
                    tool_calls.append({"name": block.name, "input_keys": list(block.input.keys())})

            await ws.broadcast(run_id, {
                "type": "transcript",
                "data": {
                    "agent_id": orch_id,
                    "messages": [{
                        "role": "assistant",
                        "text": text_parts[0][:500] if text_parts else "",
                        "tool_calls": tool_calls,
                        "turn": turn,
                        "tokens": total_tokens,
                    }],
                },
            })

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if tool_use_blocks:
                tool_results = []
                terminal = False

                for block in tool_use_blocks:
                    # Broadcast that we're executing a tool
                    await ws.broadcast(run_id, {
                        "type": "transcript",
                        "data": {
                            "agent_id": orch_id,
                            "messages": [{
                                "role": "tool_executing",
                                "tool": block.name,
                                "input_preview": str(block.input)[:200],
                            }],
                        },
                    })

                    result = await execute_orchestrator_tool(
                        block.name, block.input, run_id, state, ws,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                    # Store + broadcast tool result
                    await state.append_transcript(orch_id, [
                        TranscriptMessage(
                            role="tool_result",
                            content=result[:2000],
                            tool_use_id=block.id,
                            tool_name=block.name,
                        ),
                    ])
                    await ws.broadcast(run_id, {
                        "type": "transcript",
                        "data": {
                            "agent_id": orch_id,
                            "messages": [{
                                "role": "tool_result",
                                "tool": block.name,
                                "result_preview": result[:500],
                            }],
                        },
                    })

                    if block.name in ("submit_sim_spec", "report_failure"):
                        terminal = True

                messages.append({"role": "user", "content": tool_results})

                if terminal:
                    await state.update_agent(orch_id, status="done",
                                             result=f"Completed in {turn} turns")
                    return
            else:
                # No tool calls — nudge
                messages.append({
                    "role": "user",
                    "content": (
                        "You must call submit_sim_spec or report_failure now. "
                        "Do not respond with text — use the tool."
                    ),
                })

    except Exception as e:
        import traceback
        err_msg = f"{type(e).__name__}: {e}"
        traceback.print_exc()
        await state.update_agent(orch_id, status="failed", result=err_msg)
        await state.update_run(run_id, status="failed", error=err_msg)
        await ws.broadcast(run_id, {"type": "error", "data": {"error": err_msg}})
