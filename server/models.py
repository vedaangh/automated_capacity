"""Pydantic models for the server's domain objects."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from shared.protocol import now_iso


# ---------------------------------------------------------------------------
# SimSpec — what the orchestrator designs, engineer builds, scientist uses
# ---------------------------------------------------------------------------

class SimSpec(BaseModel):
    name: str
    description: str
    instance_type: str = "c5.2xlarge"
    setup_instructions: str
    metric_schema: dict[str, str]       # e.g. {"throughput": "float", "loss": "float"}
    mutable_files: list[str]            # files the scientist can modify
    constraints: list[str]              # rules for the scientist
    validation_criteria: list[str]      # how engineer validates the sim
    data_sources: list[str]             # where to find reference data


# ---------------------------------------------------------------------------
# Finding — one result from a research agent
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    source: str         # "web_search", "web_fetch", "reasoning"
    content: str
    url: str | None = None


# ---------------------------------------------------------------------------
# AgentState — tracks one agent (engineer or scientist)
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    id: str
    run_id: str
    role: Literal["orchestrator", "engineer", "scientist"]
    status: Literal["pending", "running", "done", "failed", "timeout"] = "pending"
    ec2_instance_id: str | None = None
    timeout_seconds: int = 1200
    started_at: str | None = None
    tool_calls: int = 0
    tokens_used: int = 0
    last_activity: str = ""
    last_heartbeat: str | None = None
    result: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# StreamSpec — a declared UI component
# ---------------------------------------------------------------------------

class StreamSpec(BaseModel):
    id: str
    run_id: str
    component_type: str
    title: str
    config: dict[str, Any]
    created_by: str     # agent_id
    created_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# Run — one research run through the full pipeline
# ---------------------------------------------------------------------------

class Run(BaseModel):
    id: str
    status: Literal[
        "research", "deciding", "engineering", "science", "complete", "failed"
    ] = "research"
    question: str
    sim_spec: SimSpec | None = None
    research_findings: list[dict[str, Any]] | None = None
    findings: str | None = None         # final scientist output
    error: str | None = None
    engineer_timeout: int = 1200        # seconds
    scientist_timeout: int = 1200       # seconds
    model: str = ""                     # Bedrock model ID
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# API request/response wrappers
# ---------------------------------------------------------------------------

class CreateRunRequest(BaseModel):
    question: str
    engineer_timeout: int | None = None   # seconds, default from config
    scientist_timeout: int | None = None  # seconds, default from config
    model: str | None = None              # Bedrock model ID, default from config


class RunResponse(BaseModel):
    run: Run
    agents: list[AgentState] = []
    streams: list[StreamSpec] = []
