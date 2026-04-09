"""FastAPI application."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routes import agents as agents_routes
from server.routes import runs as runs_routes
from server.routes import streams as streams_routes
from server.routes import ws as ws_routes
from server.state import StateManager
from server.ws_manager import WSManager
from shared.config import DATA_DIR


def create_app(data_dir: str = DATA_DIR) -> FastAPI:
    state = StateManager(data_dir=data_dir)
    ws_manager = WSManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await state.init_db()
        yield

    app = FastAPI(title="Automated Research System", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.state_manager = state
    app.state.ws_manager = ws_manager

    # Init routes
    agents_routes.init(state, ws_manager)
    streams_routes.init(state, ws_manager)
    ws_routes.init(state, ws_manager)

    def on_run_created(run_id: str):
        task = asyncio.create_task(_launch_orchestrator(run_id, state, ws_manager))
        task.add_done_callback(_handle_task_exception)

    runs_routes.init(state, ws_manager, on_run_created=on_run_created)

    app.include_router(runs_routes.router)
    app.include_router(agents_routes.router)
    app.include_router(streams_routes.router)
    app.include_router(ws_routes.router)

    return app


def _handle_task_exception(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        import traceback
        print(f"[app] Background task crashed: {exc}")
        traceback.print_exception(type(exc), exc, exc.__traceback__)


async def _launch_orchestrator(run_id: str, state: StateManager, ws: WSManager):
    try:
        from orchestrator.loop import run_orchestrator
        await run_orchestrator(run_id, state, ws)
    except Exception as e:
        import traceback
        print(f"[app] Orchestrator error: {e}")
        traceback.print_exc()
        await state.update_run(run_id, status="failed", error=str(e))
        await ws.broadcast(run_id, {"type": "error", "data": {"error": str(e)}})
