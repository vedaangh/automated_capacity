"""Orchestrator tool definitions and execution."""

from __future__ import annotations

import json
from typing import Any

from agents.research import format_findings_for_orchestrator, run_parallel_research
from server.models import SimSpec
from server.state import StateManager
from server.ws_manager import WSManager
from shared.config import ENGINEER_TIMEOUT, SCIENTIST_TIMEOUT
from shared.protocol import now_iso


ORCHESTRATOR_TOOLS = [
    {
        "name": "run_research",
        "description": (
            "Launch parallel research agents that search the web for information. "
            "Provide 3-6 specific search queries. Results are gathered and returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 3-6 specific research queries",
                    "minItems": 1,
                    "maxItems": 8,
                },
            },
            "required": ["queries"],
        },
    },
    {
        "name": "submit_sim_spec",
        "description": (
            "Submit a complete simulation specification. An engineer agent will "
            "build it on a remote EC2 instance, then a scientist agent will run "
            "experiments. This is your final action — the orchestrator exits after this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sim_spec": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "instance_type": {"type": "string", "default": "c5.2xlarge"},
                        "setup_instructions": {"type": "string"},
                        "metric_schema": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "mutable_files": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "constraints": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "validation_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "data_sources": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "name", "description", "setup_instructions",
                        "metric_schema", "mutable_files", "constraints",
                        "validation_criteria", "data_sources",
                    ],
                },
            },
            "required": ["sim_spec"],
        },
    },
    {
        "name": "report_failure",
        "description": "Report that no viable simulation can be designed for this research question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
            },
            "required": ["reason"],
        },
    },
]


async def execute_orchestrator_tool(
    name: str,
    input: dict[str, Any],
    run_id: str,
    state: StateManager,
    ws: WSManager,
) -> str:
    """Execute an orchestrator tool. Returns result string for Claude."""

    if name == "run_research":
        return await _execute_run_research(input, run_id, state, ws)
    elif name == "submit_sim_spec":
        return await _execute_submit_sim_spec(input, run_id, state, ws)
    elif name == "report_failure":
        return await _execute_report_failure(input, run_id, state, ws)
    else:
        return f"Unknown tool: {name}"


async def _execute_run_research(
    input: dict, run_id: str, state: StateManager, ws: WSManager,
) -> str:
    queries = input["queries"]

    await state.update_run(run_id, status="research")
    await ws.broadcast(run_id, {
        "type": "phase_change",
        "data": {"status": "research"},
    })

    findings = await run_parallel_research(queries)

    await state.update_run(run_id, status="deciding", research_findings=findings)
    await ws.broadcast(run_id, {
        "type": "phase_change",
        "data": {"status": "deciding"},
    })

    return format_findings_for_orchestrator(findings)


async def _execute_submit_sim_spec(
    input: dict, run_id: str, state: StateManager, ws: WSManager,
) -> str:
    spec_data = input["sim_spec"]
    sim_spec = SimSpec(**spec_data)

    # Save spec and create agent records
    await state.update_run(run_id, status="engineering", sim_spec=sim_spec)

    eng = await state.create_agent(run_id, "engineer", ENGINEER_TIMEOUT)
    sci = await state.create_agent(run_id, "scientist", SCIENTIST_TIMEOUT)

    await state.update_agent(eng.id, status="running", started_at=now_iso())

    await ws.broadcast(run_id, {
        "type": "phase_change",
        "data": {"status": "engineering", "sim_spec": spec_data},
    })

    # Spawn EC2 instance
    try:
        from infra.aws import spawn_agent_ec2
    except ImportError:
        # Fall back to local execution
        try:
            from infra.local import spawn_agent_local
            await spawn_agent_local(run_id, state, sim_spec)
            return f"Simulation spec submitted. Engineer agent {eng.id} spawned locally."
        except ImportError:
            pass
        return f"Simulation spec submitted. Engineer agent {eng.id} created (no spawner available — manual launch needed)."

    run = await state.get_run(run_id)
    from shared.protocol import AgentPayload
    import os

    payload = AgentPayload(
        run_id=run_id,
        server_url=os.environ.get("SERVER_URL", f"http://localhost:{os.environ.get('SERVER_PORT', '8420')}"),
        engineer_agent_id=eng.id,
        scientist_agent_id=sci.id,
        engineer_timeout=ENGINEER_TIMEOUT,
        scientist_timeout=SCIENTIST_TIMEOUT,
        sim_spec=spec_data,
        research_traces=run.research_findings or [],
    )

    instance_id = await spawn_agent_ec2(run_id, payload.model_dump_json())
    await state.update_agent(eng.id, ec2_instance_id=instance_id)

    return f"Simulation spec submitted. Engineer agent {eng.id} launched on EC2 {instance_id}."


async def _execute_report_failure(
    input: dict, run_id: str, state: StateManager, ws: WSManager,
) -> str:
    reason = input["reason"]
    await state.update_run(run_id, status="failed", error=reason)
    await ws.broadcast(run_id, {
        "type": "error",
        "data": {"error": reason},
    })
    return f"Run marked as failed: {reason}"
