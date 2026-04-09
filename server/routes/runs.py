"""Run routes: create and query research runs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.models import CreateRunRequest, Run, RunResponse
from server.state import StateManager
from server.ws_manager import WSManager

router = APIRouter()

state: StateManager = None  # type: ignore
ws: WSManager = None  # type: ignore

# This gets set by app.py — the function to call when a run is created
_on_run_created = None


def init(state_manager: StateManager, ws_manager: WSManager,
         on_run_created=None) -> None:
    global state, ws, _on_run_created
    state = state_manager
    ws = ws_manager
    _on_run_created = on_run_created


@router.post("/runs", response_model=RunResponse)
async def create_run(body: CreateRunRequest):
    run = await state.create_run(body.question)

    # Fire the orchestrator as a background task (if configured)
    if _on_run_created:
        _on_run_created(run.id)

    return RunResponse(run=run)


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    run = await state.get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    agents = await state.get_agents_for_run(run_id)
    streams = await state.get_streams_for_run(run_id)
    return RunResponse(run=run, agents=agents, streams=streams)


@router.get("/runs", response_model=list[Run])
async def list_runs(limit: int = 50):
    return await state.list_runs(limit)
