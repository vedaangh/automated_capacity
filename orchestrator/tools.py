"""Orchestrator tool definitions and execution."""

from __future__ import annotations

import asyncio
from typing import Any

from agents.research import format_findings_for_orchestrator, run_parallel_research
from server.models import SimSpec
from server.state import StateManager
from server.ws_manager import WSManager
from shared.protocol import now_iso


ORCHESTRATOR_TOOLS = [
    {
        "name": "run_research",
        "description": (
            "Launch parallel research agents that search the web for information. "
            "Provide 3-6 specific search queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific research queries",
                },
            },
            "required": ["queries"],
        },
    },
    {
        "name": "submit_sim_spec",
        "description": (
            "Submit a simulation specification. An engineer agent will build it, "
            "then a scientist will run experiments. This is your final action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "instance_type": {"type": "string", "default": "c5.2xlarge"},
                "setup_instructions": {"type": "string"},
                "metric_schema": {"type": "object", "additionalProperties": {"type": "string"}},
                "mutable_files": {"type": "array", "items": {"type": "string"}},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "validation_criteria": {"type": "array", "items": {"type": "string"}},
                "data_sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "description", "setup_instructions", "metric_schema",
                         "mutable_files", "constraints", "validation_criteria", "data_sources"],
        },
    },
    {
        "name": "report_failure",
        "description": "Report that no viable simulation can be designed.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


async def execute_orchestrator_tool(
    name: str, input: dict[str, Any],
    run_id: str, state: StateManager, ws: WSManager,
) -> str:
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

    # Broadcast queries so the UI can show parallel blocks immediately
    await ws.broadcast(run_id, {
        "type": "phase_change",
        "data": {
            "status": "research",
            "queries": queries,
        },
    })
    await ws.broadcast(run_id, {
        "type": "research_update",
        "data": {
            "agents": [{"query": q, "status": "running", "findings": ""} for q in queries],
        },
    })

    # Run in parallel, broadcast each as it completes
    import asyncio as _aio
    from agents.research import research_single_query

    tasks = {_aio.create_task(research_single_query(q)): q for q in queries}
    findings = []
    completed_agents = []

    for coro in _aio.as_completed(tasks.keys()):
        try:
            result = await coro
        except Exception as e:
            result = []
            # Find which query this was
        # Find the query for this task
        query = None
        for task, q in tasks.items():
            if task.done() and q not in [a["query"] for a in completed_agents]:
                query = q
                break
        if not query:
            query = "unknown"

        entry = {"query": query, "results": result}
        findings.append(entry)
        completed_agents.append({
            "query": query,
            "status": "done",
            "findings": format_findings_for_orchestrator([entry])[:500],
        })

        # Broadcast progress: show which are done and which are still running
        all_agents = []
        for q in queries:
            done_agent = next((a for a in completed_agents if a["query"] == q), None)
            if done_agent:
                all_agents.append(done_agent)
            else:
                all_agents.append({"query": q, "status": "running", "findings": ""})

        await ws.broadcast(run_id, {
            "type": "research_update",
            "data": {"agents": all_agents},
        })

    await state.update_run(run_id, status="deciding", research_findings=findings)
    await ws.broadcast(run_id, {"type": "phase_change", "data": {"status": "deciding"}})
    return format_findings_for_orchestrator(findings)


async def _execute_submit_sim_spec(
    input: dict, run_id: str, state: StateManager, ws: WSManager,
) -> str:
    try:
        sim_spec = SimSpec(**input)
    except Exception as e:
        return f"Error parsing sim spec: {e}. Keys: {list(input.keys())}"

    # Save spec and create agent records (use per-run timeouts)
    run = await state.get_run(run_id)
    eng_timeout = run.engineer_timeout if run else 1200
    sci_timeout = run.scientist_timeout if run else 1200

    await state.update_run(run_id, status="engineering", sim_spec=sim_spec)
    eng = await state.create_agent(run_id, "engineer", eng_timeout)
    sci = await state.create_agent(run_id, "scientist", sci_timeout)

    # Get research traces for the agents
    run = await state.get_run(run_id)
    research_traces = run.research_findings or []

    # Launch engineer → scientist as a background task (same process)
    from agents.harness import run_both_phases
    asyncio.create_task(run_both_phases(
        run_id=run_id,
        sim_spec=input,
        research_traces=research_traces,
        engineer_timeout=eng_timeout,
        scientist_timeout=sci_timeout,
        model=run.model or "",
        state=state,
        ws=ws,
    ))

    return f"Sim spec submitted. Engineer {eng.id} starting in lab/{run_id}/."


async def _execute_report_failure(
    input: dict, run_id: str, state: StateManager, ws: WSManager,
) -> str:
    reason = input["reason"]
    await state.update_run(run_id, status="failed", error=reason)
    await ws.broadcast(run_id, {"type": "error", "data": {"error": reason}})
    return f"Run failed: {reason}"
