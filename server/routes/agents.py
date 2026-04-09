"""Agent callback routes: heartbeat, transcript, done."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.state import StateManager
from server.ws_manager import WSManager
from shared.protocol import DoneBody, HeartbeatBody, TranscriptBody, now_iso

router = APIRouter()

# These get set by app.py at startup
state: StateManager = None  # type: ignore
ws: WSManager = None  # type: ignore


def init(state_manager: StateManager, ws_manager: WSManager) -> None:
    global state, ws
    state = state_manager
    ws = ws_manager


@router.post("/agents/{agent_id}/heartbeat")
async def heartbeat(agent_id: str, body: HeartbeatBody):
    agent = await state.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")

    await state.update_agent(
        agent_id,
        tool_calls=body.tool_calls,
        tokens_used=body.tokens,
        last_activity=body.last_activity,
        last_heartbeat=now_iso(),
    )

    await ws.broadcast(agent.run_id, {
        "type": "heartbeat",
        "data": {
            "agent_id": agent_id,
            "tool_calls": body.tool_calls,
            "tokens": body.tokens,
            "last_activity": body.last_activity,
        },
    })
    return {"ok": True}


@router.post("/agents/{agent_id}/transcript")
async def transcript(agent_id: str, body: TranscriptBody):
    agent = await state.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")

    await state.append_transcript(agent_id, body.messages)

    # Truncate large content for WS broadcast (keep it under ~4KB per message)
    truncated = []
    for msg in body.messages:
        d = msg.model_dump()
        if isinstance(d.get("content"), str) and len(d["content"]) > 2000:
            d["content"] = d["content"][:2000] + "...[truncated]"
        truncated.append(d)

    await ws.broadcast(agent.run_id, {
        "type": "transcript",
        "data": {"agent_id": agent_id, "messages": truncated},
    })
    return {"ok": True}


@router.post("/agents/{agent_id}/done")
async def done(agent_id: str, body: DoneBody):
    agent = await state.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")

    await state.update_agent(agent_id, status=body.status, result=body.result)

    # Advance the run to the next phase
    await _advance_run_phase(agent, body)
    return {"ok": True}


async def _advance_run_phase(agent, body: DoneBody):
    """Transition run status based on which agent just finished."""
    if agent.role == "engineer":
        if body.status == "done":
            sci_id = agent.run_id + "-sci"
            await state.update_agent(sci_id, status="running", started_at=now_iso())
            await state.update_run(agent.run_id, status="science")
            await ws.broadcast(agent.run_id, {
                "type": "phase_change",
                "data": {"status": "science"},
            })
        else:
            err = f"Engineer {body.status}: {(body.result or '')[:500]}"
            await state.update_run(agent.run_id, status="failed", error=err)
            await ws.broadcast(agent.run_id, {
                "type": "error",
                "data": {"error": err, "phase": "engineering"},
            })

    elif agent.role == "scientist":
        if body.status == "done":
            await state.update_run(agent.run_id, status="complete", findings=body.result)
            await ws.broadcast(agent.run_id, {
                "type": "complete",
                "data": {"findings": body.result},
            })
        else:
            err = f"Scientist {body.status}: {(body.result or '')[:500]}"
            await state.update_run(agent.run_id, status="failed", error=err)
            await ws.broadcast(agent.run_id, {
                "type": "error",
                "data": {"error": err, "phase": "science"},
            })
