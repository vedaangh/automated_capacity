/**
 * REST API client for the Automated Capacity server.
 * Server runs on port 8420 by default.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8420";

// ---------------------------------------------------------------------------
// Backend types (mirrors server/models.py + shared/protocol.py)
// ---------------------------------------------------------------------------

export interface SimSpec {
  name: string;
  description: string;
  instance_type: string;
  setup_instructions: string;
  metric_schema: Record<string, string>;
  mutable_files: string[];
  constraints: string[];
  validation_criteria: string[];
  data_sources: string[];
}

export interface AgentState {
  id: string;
  run_id: string;
  role: "orchestrator" | "engineer" | "scientist";
  status: "pending" | "running" | "done" | "failed" | "timeout";
  ec2_instance_id: string | null;
  timeout_seconds: number;
  started_at: string | null;
  tool_calls: number;
  tokens_used: number;
  last_activity: string;
  last_heartbeat: string | null;
  result: string | null;
  created_at: string;
  updated_at: string;
}

export interface StreamSpec {
  id: string;
  run_id: string;
  component_type:
    | "line_chart"
    | "scatter_plot"
    | "bar_chart"
    | "heatmap"
    | "text_log"
    | "video_stream"
    | "table"
    | "metric_card";
  title: string;
  config: Record<string, unknown>;
  created_by: string;
  created_at: string;
}

export type RunStatus =
  | "research"
  | "deciding"
  | "engineering"
  | "science"
  | "complete"
  | "failed";

export interface Run {
  id: string;
  status: RunStatus;
  question: string;
  sim_spec: SimSpec | null;
  research_findings: Record<string, unknown>[] | null;
  findings: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunResponse {
  run: Run;
  agents: AgentState[];
  streams: StreamSpec[];
}

// ---------------------------------------------------------------------------
// WebSocket event types
// ---------------------------------------------------------------------------

export type WSEventType =
  | "snapshot"
  | "phase_change"
  | "heartbeat"
  | "transcript"
  | "research_update"
  | "stream_created"
  | "stream_data"
  | "complete"
  | "error";

export interface WSEvent {
  type: WSEventType;
  data: Record<string, unknown>;
  ts: string;
}

export interface TranscriptMessage {
  role: "user" | "assistant" | "tool_result";
  content: unknown;
  ts: string;
  tool_use_id?: string;
  tool_name?: string;
}

// ---------------------------------------------------------------------------
// REST calls
// ---------------------------------------------------------------------------

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function createRun(
  question: string,
  engineer_timeout?: number,
  scientist_timeout?: number,
): Promise<RunResponse> {
  const body: Record<string, unknown> = { question };
  if (engineer_timeout) body.engineer_timeout = engineer_timeout;
  if (scientist_timeout) body.scientist_timeout = scientist_timeout;
  return json("/runs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getRun(runId: string): Promise<RunResponse> {
  return json(`/runs/${runId}`);
}

export function listRuns(limit = 50): Promise<Run[]> {
  return json(`/runs?limit=${limit}`);
}

export interface TranscriptResult {
  [agentId: string]: {
    role: string;
    messages: TranscriptMessage[];
  };
}

export function getTranscript(runId: string): Promise<TranscriptResult> {
  return json(`/runs/${runId}/transcript`);
}

// ---------------------------------------------------------------------------
// WebSocket URL
// ---------------------------------------------------------------------------

export function wsUrl(runId: string): string {
  const base = BASE.replace(/^http/, "ws");
  return `${base}/runs/${runId}/stream`;
}
