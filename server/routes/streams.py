"""Stream routes: create UI components, push data."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.state import StateManager
from server.ws_manager import WSManager
from shared.protocol import StreamCreateBody, StreamCreateResponse, StreamDataBody

router = APIRouter()

state: StateManager = None  # type: ignore
ws: WSManager = None  # type: ignore


def init(state_manager: StateManager, ws_manager: WSManager) -> None:
    global state, ws
    state = state_manager
    ws = ws_manager


@router.post("/runs/{run_id}/streams", response_model=StreamCreateResponse)
async def create_stream(run_id: str, body: StreamCreateBody):
    run = await state.get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")

    stream_id = await state.create_stream(
        run_id=run_id,
        component_type=body.component_type,
        title=body.title,
        config=body.config,
    )

    await ws.broadcast(run_id, {
        "type": "stream_created",
        "data": {
            "stream_id": stream_id,
            "component_type": body.component_type,
            "title": body.title,
            "config": body.config,
        },
    })

    return StreamCreateResponse(stream_id=stream_id)


@router.post("/runs/{run_id}/streams/{stream_id}/data")
async def stream_data(run_id: str, stream_id: str, body: StreamDataBody):
    # Relay only — no storage
    await ws.broadcast(run_id, {
        "type": "stream_data",
        "data": {"stream_id": stream_id, "points": body.points},
    })
    return {"ok": True}
