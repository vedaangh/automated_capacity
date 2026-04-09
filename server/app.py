"""FastAPI application: assembles routes, manages lifecycle."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from server.routes import agents as agents_routes
from server.routes import runs as runs_routes
from server.routes import streams as streams_routes
from server.routes import ws as ws_routes
from server.state import StateManager
from server.ws_manager import WSManager
from shared.config import DATA_DIR, HEARTBEAT_DEAD_AFTER


def create_app(data_dir: str = DATA_DIR) -> FastAPI:
    state = StateManager(data_dir=data_dir)
    ws_manager = WSManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await state.init_db()
        watchdog_task = asyncio.create_task(_watchdog_loop(state, ws_manager))
        yield
        watchdog_task.cancel()

    app = FastAPI(title="Automated Research System", lifespan=lifespan)

    # Stash on app for orchestrator access
    app.state.state_manager = state
    app.state.ws_manager = ws_manager

    # Init route modules with shared state
    agents_routes.init(state, ws_manager)
    streams_routes.init(state, ws_manager)
    ws_routes.init(state, ws_manager)

    # runs_routes gets a callback to launch the orchestrator
    def on_run_created(run_id: str):
        task = asyncio.create_task(_launch_orchestrator(run_id, state, ws_manager))
        task.add_done_callback(_handle_task_exception)

    runs_routes.init(state, ws_manager, on_run_created=on_run_created)

    # Include routers
    app.include_router(runs_routes.router)
    app.include_router(agents_routes.router)
    app.include_router(streams_routes.router)
    app.include_router(ws_routes.router)

    return app


def _handle_task_exception(task: asyncio.Task) -> None:
    """Log exceptions from background asyncio tasks instead of swallowing them."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        print(f"[app] Background task crashed: {exc}")


async def _launch_orchestrator(run_id: str, state: StateManager, ws: WSManager):
    """Placeholder — will be wired to orchestrator.loop.run_orchestrator."""
    # Import deferred to avoid circular imports at module level
    try:
        from orchestrator.loop import run_orchestrator
        await run_orchestrator(run_id, state, ws)
    except ImportError:
        # Orchestrator not built yet — just log
        print(f"[app] Orchestrator not available, run {run_id} will stay in 'research' status")
    except Exception as e:
        await state.update_run(run_id, status="failed", error=str(e))
        await ws.broadcast(run_id, {
            "type": "error",
            "data": {"error": str(e)},
        })


async def _watchdog_loop(state: StateManager, ws: WSManager):
    """Check for dead agents every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        try:
            running = await state.get_running_agents()
            now = datetime.now(timezone.utc)
            for agent in running:
                if not agent.last_heartbeat:
                    continue  # hasn't sent first heartbeat yet (cold start grace)
                last = datetime.fromisoformat(agent.last_heartbeat)
                elapsed = (now - last).total_seconds()
                if elapsed > HEARTBEAT_DEAD_AFTER:
                    print(f"[watchdog] Agent {agent.id} presumed dead ({elapsed:.0f}s since last heartbeat)")
                    await state.update_agent(agent.id, status="failed",
                                             result="Agent presumed dead (no heartbeat)")
                    # Trigger phase advancement (same as done handler)
                    from shared.protocol import DoneBody
                    body = DoneBody(result="Agent presumed dead (no heartbeat)", status="failed")
                    await agents_routes._advance_run_phase(agent, body)
        except Exception as e:
            print(f"[watchdog] Error: {e}")
