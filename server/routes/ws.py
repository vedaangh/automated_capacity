"""WebSocket route: stream events to the browser."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.models import RunResponse
from server.state import StateManager
from server.ws_manager import WSManager
from shared.protocol import now_iso

router = APIRouter()

state: StateManager = None  # type: ignore
ws_manager: WSManager = None  # type: ignore


def init(state_manager: StateManager, manager: WSManager) -> None:
    global state, ws_manager
    state = state_manager
    ws_manager = manager


@router.websocket("/runs/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: str):
    await websocket.accept()

    # Check run exists
    run = await state.get_run(run_id)
    if not run:
        await websocket.send_json({
            "type": "error",
            "data": {"error": f"Run {run_id} not found"},
            "ts": now_iso(),
        })
        await websocket.close()
        return

    # Register this connection
    ws_manager.connect(run_id, websocket)

    try:
        # Send initial snapshot
        agents = await state.get_agents_for_run(run_id)
        streams = await state.get_streams_for_run(run_id)
        snapshot = RunResponse(run=run, agents=agents, streams=streams)
        await websocket.send_json({
            "type": "snapshot",
            "data": json.loads(snapshot.model_dump_json()),
            "ts": now_iso(),
        })

        # Keep alive — incoming messages are just keepalive pings or cancel
        while True:
            data = await websocket.receive_text()
            if data == "cancel":
                # Could implement run cancellation here
                pass

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(run_id, websocket)
