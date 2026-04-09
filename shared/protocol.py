"""Wire protocol types shared between agent (EC2) and server."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Agent → Server payloads
# ---------------------------------------------------------------------------

class HeartbeatBody(BaseModel):
    tool_calls: int = 0
    tokens: int = 0
    last_activity: str = ""


class TranscriptMessage(BaseModel):
    role: Literal["user", "assistant", "tool_result"]
    content: Any  # str or list[ContentBlock]
    ts: str = Field(default_factory=now_iso)
    tool_use_id: str | None = None
    tool_name: str | None = None


class TranscriptBody(BaseModel):
    messages: list[TranscriptMessage]


class DoneBody(BaseModel):
    result: str
    status: Literal["done", "failed", "timeout"] = "done"


class StreamCreateBody(BaseModel):
    component_type: Literal[
        "line_chart", "scatter_plot", "bar_chart", "heatmap",
        "text_log", "video_stream", "table", "metric_card",
    ]
    title: str
    config: dict[str, Any]


class StreamCreateResponse(BaseModel):
    stream_id: str


class StreamDataBody(BaseModel):
    points: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Server → Browser WebSocket events
# ---------------------------------------------------------------------------

class WSEvent(BaseModel):
    type: Literal[
        "snapshot", "phase_change", "heartbeat", "transcript",
        "stream_created", "stream_data", "complete", "error",
    ]
    data: dict[str, Any]
    ts: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# EC2 boot payload (server → agent via user-data)
# ---------------------------------------------------------------------------

class AgentPayload(BaseModel):
    run_id: str
    server_url: str
    engineer_agent_id: str
    scientist_agent_id: str
    engineer_timeout: int
    scientist_timeout: int
    sim_spec: dict[str, Any]
    research_traces: list[dict[str, Any]]
    # No API key needed — Bedrock auth via IAM role on EC2
