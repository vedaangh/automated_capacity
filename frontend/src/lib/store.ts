"use client";

import { useCallback, useRef, useSyncExternalStore } from "react";
import type {
  WSEvent,
  Run,
  RunResponse,
  AgentState,
  StreamSpec,
  TranscriptMessage,
} from "./api";

// ---------------------------------------------------------------------------
// Client-side state shape
// ---------------------------------------------------------------------------

export interface LiveStream {
  spec: StreamSpec;
  data: Record<string, unknown>[][]; // batches of points
}

export interface ResearchAgentState {
  query: string;
  status: "running" | "done";
  findings: string;
}

export interface SessionState {
  run: Run;
  agents: AgentState[];
  streams: Map<string, LiveStream>;
  transcript: TranscriptMessage[];
  researchAgents: ResearchAgentState[];
  // Derived timeline entries for the UI
  timeline: TimelineEntry[];
}

export type TimelineEntryType =
  | "prompt"
  | "research"
  | "engineering"
  | "science"
  | "complete"
  | "error";

export interface TimelineEntry {
  id: string;
  type: TimelineEntryType;
  timestamp: string;
  content: string;
  details?: string; // expandable
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export interface Store {
  sessions: Map<string, SessionState>;
  activeRunId: string | null;
  runList: Run[];
}

type Listener = () => void;

export function createStore() {
  let state: Store = {
    sessions: new Map(),
    activeRunId: null,
    runList: [],
  };

  const listeners = new Set<Listener>();

  function getState() {
    return state;
  }

  function emit() {
    // Create new reference so useSyncExternalStore detects change
    state = { ...state };
    for (const l of listeners) l();
  }

  function subscribe(listener: Listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  // -- Mutations --

  function setRunList(runs: Run[]) {
    state.runList = runs;
    emit();
  }

  function setActiveRun(runId: string | null) {
    state.activeRunId = runId;
    emit();
  }

  function getOrCreateSession(runId: string): SessionState {
    let s = state.sessions.get(runId);
    if (!s) {
      // Placeholder until snapshot arrives
      s = {
        run: {
          id: runId,
          status: "research",
          question: "",
          sim_spec: null,
          research_findings: null,
          findings: null,
          error: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        agents: [],
        streams: new Map(),
        transcript: [],
        researchAgents: [],
        timeline: [],
      };
      state.sessions.set(runId, s);
    }
    return s;
  }

  function handleSnapshot(runId: string, data: RunResponse) {
    const s = getOrCreateSession(runId);
    s.run = data.run;
    s.agents = data.agents;
    for (const spec of data.streams) {
      if (!s.streams.has(spec.id)) {
        s.streams.set(spec.id, { spec, data: [] });
      }
    }
    rebuildTimeline(s);
    emit();
  }

  function handlePhaseChange(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    if (data.status) s.run.status = data.status as Run["status"];
    if (data.sim_spec) s.run.sim_spec = data.sim_spec as Run["sim_spec"];
    if (data.research_findings)
      s.run.research_findings = data.research_findings as Run["research_findings"];
    rebuildTimeline(s);
    emit();
  }

  function handleHeartbeat(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    const agentId = data.agent_id as string | undefined;
    if (agentId) {
      const agent = s.agents.find((a) => a.id === agentId);
      if (agent) {
        agent.tool_calls = (data.tool_calls as number) ?? agent.tool_calls;
        agent.tokens_used = (data.tokens as number) ?? agent.tokens_used;
        agent.last_activity = (data.last_activity as string) ?? agent.last_activity;
        agent.last_heartbeat = new Date().toISOString();
      }
    }
    emit();
  }

  function handleTranscript(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    const agentId = data.agent_id as string | undefined;
    const messages = data.messages as TranscriptMessage[] | undefined;
    if (messages) {
      // Tag each message with the agent_id so the UI can filter by role
      for (const msg of messages) {
        (msg as Record<string, unknown>)._agent_id = agentId;
      }
      s.transcript.push(...messages);
      rebuildTimeline(s);
    }
    emit();
  }

  function handleResearchUpdate(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    const agents = data.agents as ResearchAgentState[] | undefined;
    if (agents) {
      s.researchAgents = agents;
      rebuildTimeline(s);
    }
    emit();
  }

  function handleStreamCreated(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    const spec = data as unknown as StreamSpec;
    if (spec.id && !s.streams.has(spec.id)) {
      s.streams.set(spec.id, { spec, data: [] });
    }
    emit();
  }

  function handleStreamData(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    const streamId = data.stream_id as string;
    const points = data.points as Record<string, unknown>[];
    if (streamId && points) {
      const stream = s.streams.get(streamId);
      if (stream) {
        stream.data.push(points);
      }
    }
    emit();
  }

  function handleComplete(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    s.run.status = "complete";
    if (data.findings) s.run.findings = data.findings as string;
    rebuildTimeline(s);
    emit();
  }

  function handleError(
    runId: string,
    data: Record<string, unknown>,
  ) {
    const s = getOrCreateSession(runId);
    s.run.status = "failed";
    s.run.error = (data.error as string) ?? "Unknown error";
    rebuildTimeline(s);
    emit();
  }

  /** Dispatch a WebSocket event into the store. */
  function dispatch(runId: string, event: WSEvent) {
    switch (event.type) {
      case "snapshot":
        handleSnapshot(runId, event.data as unknown as RunResponse);
        break;
      case "phase_change":
        handlePhaseChange(runId, event.data);
        break;
      case "heartbeat":
        handleHeartbeat(runId, event.data);
        break;
      case "transcript":
        handleTranscript(runId, event.data);
        break;
      case "research_update":
        handleResearchUpdate(runId, event.data);
        break;
      case "stream_created":
        handleStreamCreated(runId, event.data);
        break;
      case "stream_data":
        handleStreamData(runId, event.data);
        break;
      case "complete":
        handleComplete(runId, event.data);
        break;
      case "error":
        handleError(runId, event.data);
        break;
    }
  }

  return {
    getState,
    subscribe,
    dispatch,
    setRunList,
    setActiveRun,
    getOrCreateSession,
    handleSnapshot,
  };
}

// ---------------------------------------------------------------------------
// Timeline builder
// ---------------------------------------------------------------------------

function rebuildTimeline(s: SessionState) {
  const entries: TimelineEntry[] = [];
  const now = new Date().toISOString();

  // 1. Prompt
  entries.push({
    id: "prompt",
    type: "prompt",
    timestamp: s.run.created_at,
    content: s.run.question,
  });

  // 2. Research findings
  if (
    s.run.research_findings &&
    s.run.research_findings.length > 0 &&
    s.run.status !== "research"
  ) {
    const summary = s.run.research_findings
      .map((f) => {
        const content = (f.content as string) ?? "";
        return content.length > 200 ? content.slice(0, 200) + "..." : content;
      })
      .join("\n");
    entries.push({
      id: "research",
      type: "research",
      timestamp: s.run.updated_at,
      content: `Found ${s.run.research_findings.length} research results`,
      details: summary,
    });
  }

  // 3. Engineering
  if (
    ["engineering", "science", "complete"].includes(s.run.status) &&
    s.run.sim_spec
  ) {
    const spec = s.run.sim_spec;
    entries.push({
      id: "engineering",
      type: "engineering",
      timestamp: s.run.updated_at,
      content: `Building: ${spec.name}`,
      details: `${spec.description}\nMetrics: ${Object.keys(spec.metric_schema).join(", ")}\nMutable: ${spec.mutable_files.join(", ")}`,
    });
  }

  // 4. Transcript entries from agents (latest activity)
  const agentMessages = s.transcript.filter(
    (m) => m.role === "assistant" && typeof m.content === "string",
  );
  for (const msg of agentMessages.slice(-10)) {
    const text = msg.content as string;
    if (text.length > 0) {
      entries.push({
        id: `t-${msg.ts}`,
        type: s.run.status === "science" ? "science" : "engineering",
        timestamp: msg.ts,
        content: text.length > 300 ? text.slice(0, 300) + "..." : text,
      });
    }
  }

  // 5. Complete
  if (s.run.status === "complete" && s.run.findings) {
    entries.push({
      id: "complete",
      type: "complete",
      timestamp: s.run.updated_at,
      content: s.run.findings,
    });
  }

  // 6. Error
  if (s.run.status === "failed" && s.run.error) {
    entries.push({
      id: "error",
      type: "error",
      timestamp: s.run.updated_at,
      content: s.run.error,
    });
  }

  s.timeline = entries;
}

// ---------------------------------------------------------------------------
// React hook
// ---------------------------------------------------------------------------

export type StoreInstance = ReturnType<typeof createStore>;

export function useStore(store: StoreInstance) {
  return useSyncExternalStore(store.subscribe, store.getState, store.getState);
}
