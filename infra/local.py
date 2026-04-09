"""Local subprocess fallback for development (no EC2 needed)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from server.models import SimSpec
from server.state import StateManager
from shared.config import ENGINEER_TIMEOUT, SCIENTIST_TIMEOUT
from shared.protocol import AgentPayload


async def spawn_agent_local(
    run_id: str,
    state: StateManager,
    sim_spec: SimSpec,
    server_url: str | None = None,
) -> None:
    """Spawn the agent harness as a local subprocess.

    The subprocess runs both engineer and scientist phases sequentially,
    same as it would on EC2, but on the local machine.
    """
    if server_url is None:
        port = os.environ.get("SERVER_PORT", "8420")
        server_url = f"http://localhost:{port}"

    run = await state.get_run(run_id)

    payload = AgentPayload(
        run_id=run_id,
        server_url=server_url,
        engineer_agent_id=f"{run_id}-eng",
        scientist_agent_id=f"{run_id}-sci",
        engineer_timeout=ENGINEER_TIMEOUT,
        scientist_timeout=SCIENTIST_TIMEOUT,
        sim_spec=sim_spec.model_dump(),
        research_traces=run.research_findings or [],
    )

    # Write payload to temp file
    payload_path = Path(f"/tmp/agent_payload_{run_id}.json")
    payload_path.write_text(payload.model_dump_json())

    # Spawn as background subprocess
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "agents.harness",
        "--payload", str(payload_path),
        cwd=os.getcwd(),
        env=os.environ.copy(),
    )

    # Don't await — let it run in the background
    # The harness will POST heartbeats/transcripts/done to the server
    asyncio.create_task(_wait_and_cleanup(proc, payload_path))


async def _wait_and_cleanup(proc, payload_path: Path):
    """Wait for subprocess to finish and clean up."""
    await proc.wait()
    try:
        payload_path.unlink(missing_ok=True)
    except Exception:
        pass
