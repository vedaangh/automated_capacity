"""Orchestrator: Claude tool-use loop that drives the research pipeline."""

from __future__ import annotations

import anthropic

from orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from orchestrator.tools import ORCHESTRATOR_TOOLS, execute_orchestrator_tool
from server.state import StateManager
from server.ws_manager import WSManager
from shared.config import AWS_REGION, ORCHESTRATOR_MODEL
from shared.protocol import now_iso


async def run_orchestrator(run_id: str, state: StateManager, ws: WSManager) -> None:
    """Main orchestrator loop. Runs as an asyncio task in the server process."""
    run = await state.get_run(run_id)
    if not run:
        return

    client = anthropic.AsyncAnthropicBedrock(aws_region=AWS_REGION)
    messages = [{"role": "user", "content": f"Research question: {run.question}"}]

    try:
        for turn in range(20):  # max turns to prevent infinite loops
            response = await client.messages.create(
                model=ORCHESTRATOR_MODEL,
                max_tokens=4096,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                messages=messages,
                tools=ORCHESTRATOR_TOOLS,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Opus responded with text instead of calling a tool.
                # Nudge it to call submit_sim_spec or report_failure.
                messages.append({
                    "role": "user",
                    "content": (
                        "You must call submit_sim_spec or report_failure now. "
                        "Do not respond with text — use the tool."
                    ),
                })
                continue  # retry the loop (max 20 turns protects against infinite)

            # Execute tool calls
            tool_results = []
            terminal = False

            for block in response.content:
                if block.type != "tool_use":
                    continue

                result = await execute_orchestrator_tool(
                    block.name, block.input, run_id, state, ws,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

                # Terminal tools: orchestrator's job is done
                if block.name in ("submit_sim_spec", "report_failure"):
                    terminal = True

            messages.append({"role": "user", "content": tool_results})

            if terminal:
                return

    except Exception as e:
        await state.update_run(run_id, status="failed", error=str(e))
        await ws.broadcast(run_id, {
            "type": "error",
            "data": {"error": f"Orchestrator error: {e}"},
        })
