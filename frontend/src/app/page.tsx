"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import Sidebar from "@/components/Sidebar";
import ChatView from "@/components/ChatView";
import { mockSessions } from "@/lib/mock-data";
import type { Session, SimulationCard as SimCardType } from "@/lib/types";
import { createRun, listRuns, getRun, getTranscript, type WSEvent, type RunResponse, type Run, type TranscriptMessage } from "@/lib/api";
import { sanitizeDisplayText } from "@/lib/formatDisplay";
import { useRunSocket } from "@/lib/useRunSocket";
import { createStore, useStore, type LiveStream } from "@/lib/store";

/** Extract readable text from a transcript message's content (string, array of blocks, or nested) */
function formatToolInput(name: string, input: Record<string, unknown>): string {
  if (name === "bash") return String(input.command ?? "").slice(0, 120);
  if (name === "edit") return `${input.mode} ${input.path}`;
  if (name === "read") return String(input.path ?? "");
  if (name === "search") return `${input.mode}: ${input.pattern}`;
  if (name === "web_fetch") return String(input.url ?? "").slice(0, 80);
  if (name === "create_stream") return `${input.component_type}: ${input.title}`;
  if (name === "check_timer") return "";
  if (name === "signal_done") return "Handing off...";
  return JSON.stringify(input).slice(0, 80);
}

function extractText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    const parts: string[] = [];
    for (const block of content) {
      if (typeof block === "string") { parts.push(block); continue; }
      if (block?.type === "text" && block?.text) { parts.push(block.text); continue; }
      if (block?.type === "tool_use") {
        const desc = formatToolInput(block.name, block.input ?? {});
        parts.push(desc ? `▸ ${block.name}  ${desc}` : `▸ ${block.name}`);
        continue;
      }
      // Skip tool_results in the trace — they're noisy
    }
    return parts.filter(Boolean).join("\n");
  }
  if (content && typeof content === "object") {
    const c = content as Record<string, unknown>;
    if (c.text) return String(c.text);
    if (c.tool && c.input_preview) return `▸ ${c.tool}  ${String(c.input_preview).slice(0, 120)}`;
    if (c.tool && c.result_preview) return `  ↳ ${String(c.result_preview).slice(0, 150)}`;
    if (c.tool) return `▸ ${c.tool}`;
  }
  return String(content ?? "");
}

/** Extract only assistant thinking text (ignores tool_result / user rows). */
function extractThinking(transcript: TranscriptMessage[]): string[] {
  const results: string[] = [];
  for (const m of transcript) {
    if (m.role !== "assistant") continue;
    const ex = m as unknown as Record<string, unknown>;
    if (typeof ex.text === "string" && ex.text.trim()) {
      results.push(ex.text.trim());
      continue;
    }
    const content = m.content;
    if (typeof content === "string") {
      if (content.trim()) results.push(content.trim());
      continue;
    }
    if (Array.isArray(content)) {
      for (const block of content) {
        if (block?.type === "text" && block?.text?.trim()) {
          results.push(block.text.trim());
        }
      }
      continue;
    }
    if (content && typeof content === "object") {
      const c = content as Record<string, unknown>;
      if (c.text && String(c.text).trim()) results.push(String(c.text).trim());
    }
  }
  return results;
}

function dedupeThoughtChunks(chunks: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of chunks) {
    const t = raw.trim();
    if (!t) continue;
    if (seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  return out;
}

/** Extract only tool calls from a transcript (for build log) */
function extractToolCalls(transcript: TranscriptMessage[]): string[] {
  const results: string[] = [];
  for (const m of transcript) {
    const content = m.content;
    if (Array.isArray(content)) {
      for (const block of content) {
        if (block?.type === "tool_use") {
          const desc = formatToolInput(block.name, block.input ?? {});
          results.push(desc ? `▸ ${block.name}  ${desc}` : `▸ ${block.name}`);
        }
      }
    }
  }
  return results;
}

function runToSession(run: Run): Session {
  const date = new Date(run.created_at);
  const month = date.toLocaleString("en", { month: "short" });
  const day = date.getDate();
  return {
    id: run.id,
    name: run.question.length > 40 ? run.question.slice(0, 40) + "..." : run.question,
    date: `${month} ${day}`,
    status: run.status,
    runId: run.id,
    cards: [],
  };
}

function buildCardsFromStore(
  store: ReturnType<typeof createStore>,
  runId: string,
): Session["cards"] {
  const session = store.getState().sessions.get(runId);
  if (!session) return [];

  const cards: Session["cards"] = [];
  const run = session.run;

  // Prompt
  if (run.question) {
    cards.push({
      id: "prompt",
      type: "user",
      timestamp: new Date(run.created_at).toLocaleTimeString("en", { hour: "numeric", minute: "2-digit" }),
      content: {
        message: run.question,
        budget: run.engineer_timeout ? `${Math.round(run.engineer_timeout / 60)}m budget` : undefined,
      },
    });
  }

  // Helper: filter transcript by agent suffix
  const orchTranscript = session.transcript.filter((m) => {
    const aid = (m as unknown as Record<string, unknown>)._agent_id as string | undefined;
    return aid?.endsWith("-orch");
  });
  const engTranscript = session.transcript.filter((m) => {
    const aid = (m as unknown as Record<string, unknown>)._agent_id as string | undefined;
    return aid?.endsWith("-eng");
  });
  const sciTranscript = session.transcript.filter((m) => {
    const aid = (m as unknown as Record<string, unknown>)._agent_id as string | undefined;
    return aid?.endsWith("-sci");
  });

  const orchThinking = dedupeThoughtChunks(
    extractThinking(orchTranscript).map((t) => sanitizeDisplayText(t, 8000)),
  );
  const orchThinkingMerged = orchThinking.filter((t) => t.length > 0).join("\n\n");
  if (orchThinkingMerged.length > 8) {
    cards.push({
      id: "orchestrator",
      type: "orchestrator",
      timestamp: "",
      content: { thinking: orchThinkingMerged },
    });
  }

  if (session.researchAgents.length > 0) {
    const doneCount = session.researchAgents.filter((a) => a.status === "done").length;
    cards.push({
      id: "research-live",
      type: "research",
      timestamp: "",
      content: {
        summary: `Researching: ${doneCount}/${session.researchAgents.length} queries complete`,
        agents: session.researchAgents.map((a, i) => ({
          name: `Agent ${i + 1}`,
          query: a.query,
          findings: sanitizeDisplayText(
            a.findings || (a.status === "running" ? "Searching..." : ""),
            8000,
          ),
          status: a.status,
        })),
      },
    });
  }

  // Show a spinner if still thinking
  if (["research", "deciding"].includes(run.status) && orchThinking.length === 0) {
    cards.push({
      id: "status-thinking",
      type: "status",
      timestamp: "",
      content: {
        phase: run.status === "research" ? "Researching" : "Designing",
        message: run.status === "research" ? "Research agents searching..." : "Designing simulation specification...",
      },
    });
  }

  // Research findings
  if (run.research_findings && run.research_findings.length > 0) {
    const findings = run.research_findings;
    cards.push({
      id: "research",
      type: "research",
      timestamp: new Date(run.updated_at).toLocaleTimeString("en", { hour: "numeric", minute: "2-digit" }),
      content: {
        summary: `Researched ${findings.length} queries`,
        agents: findings.map((f, i) => {
          const query = (f.query as string) ?? `Query ${i + 1}`;
          const results = (f.results as Array<Record<string, unknown>>) ?? [];
          const resultText = results
            .map((r) => {
              const content = (r.content as string) ?? "";
              const url = (r.url as string) ?? "";
              const source = (r.source as string) ?? "";
              const cleaned = sanitizeDisplayText(content, 4000);
              const line = cleaned.length > 1200 ? `${cleaned.slice(0, 1200)}…` : cleaned;
              return url ? `[${source}] ${line}\n(${url})` : line;
            })
            .filter((s) => s.length > 0)
            .join("\n\n");
          return {
            name: `Agent ${i + 1}`,
            query,
            findings: resultText || (f.error as string) || "No results",
            status: "done" as const,
          };
        }),
      },
    });
  }

  // Deciding
  if (run.status === "deciding") {
    cards.push({
      id: "status-deciding",
      type: "status",
      timestamp: "",
      content: { phase: "Deciding", message: "Designing simulation specification..." },
    });
  }

  // Engineering
  if (run.sim_spec && ["engineering", "science", "complete"].includes(run.status)) {
    const engineer = session.agents.find((a) => a.role === "engineer");
    const engToolCalls = extractToolCalls(engTranscript).slice(-30);

    const engThinking = extractThinking(engTranscript).map((t) => sanitizeDisplayText(t, 12000));

    cards.push({
      id: "engineering",
      type: "engineering",
      timestamp: new Date(run.updated_at).toLocaleTimeString("en", { hour: "numeric", minute: "2-digit" }),
      content: {
        summary: `Building: ${run.sim_spec.name}`,
        status: engineer?.status === "done" ? "done" : "building",
        trace: engToolCalls.length > 0 ? engToolCalls : [`Setting up ${run.sim_spec.name}...`],
        thinking: engThinking,
        simSpec: {
          name: run.sim_spec.name,
          metric: Object.keys(run.sim_spec.metric_schema)[0] ?? "metric",
          direction: "minimize",
          timeoutSeconds: run.engineer_timeout ?? 1200,
        },
      },
    });
  }

  // Simulation streams
  if (session.streams.size > 0 && ["science", "complete"].includes(run.status)) {
    const streamIds = Array.from(session.streams.keys());
    cards.push({
      id: "simulation",
      type: "simulation",
      timestamp: "",
      content: {
        windowCount: Math.min(streamIds.length, 4),
        maxWindows: 4,
        connected: true,
        streamIds,
      },
    });
  }

  // Science phase transcript as experiment-like log
  if (["science", "complete"].includes(run.status)) {
    const sciToolCalls = extractToolCalls(sciTranscript);
    const sciThinking = extractThinking(sciTranscript);

    const sciThinkingClean = sciThinking.map((t) => sanitizeDisplayText(t, 12000));

    if (sciToolCalls.length > 0 || sciThinkingClean.length > 0) {
      cards.push({
        id: "experiments",
        type: "experiment",
        timestamp: "",
        content: {
          experiments: sciToolCalls.slice(-20).map((msg, i) => ({
            id: i + 1,
            status: "running" as const,
            description: msg,
          })),
          thinkingLines: sciThinkingClean,
        },
      });
    }
  }

  // Complete
  if (run.status === "complete" && run.findings) {
    cards.push({
      id: "findings",
      type: "findings",
      timestamp: new Date(run.updated_at).toLocaleTimeString("en", { hour: "numeric", minute: "2-digit" }),
      content: { text: run.findings },
    });
  }

  // Error
  if (run.status === "failed" && run.error) {
    cards.push({
      id: "error",
      type: "error",
      timestamp: new Date(run.updated_at).toLocaleTimeString("en", { hour: "numeric", minute: "2-digit" }),
      content: { message: run.error },
    });
  }

  return cards;
}

export default function Home() {
  const storeRef = useRef<ReturnType<typeof createStore> | null>(null);
  if (!storeRef.current) storeRef.current = createStore();
  const store = storeRef.current;

  const storeState = useStore(store);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [liveRunId, setLiveRunId] = useState<string | null>(null);
  const [backendAvailable, setBackendAvailable] = useState(false);

  // Load runs from backend on mount
  useEffect(() => {
    listRuns()
      .then(async (runs) => {
        setBackendAvailable(true);
        store.setRunList(runs);
        if (runs.length > 0) {
          const liveSessions = runs.map(runToSession);
          setSessions(liveSessions);
          setActiveId(runs[0].id);
          setLiveRunId(runs[0].id);
          // Load full state for the first run
          try {
            const full = await getRun(runs[0].id);
            store.handleSnapshot(runs[0].id, full);
            const transcript = await getTranscript(runs[0].id);
            for (const [agentId, data] of Object.entries(transcript)) {
              for (const msg of data.messages) {
                store.dispatch(runs[0].id, {
                  type: "transcript",
                  data: { agent_id: agentId, messages: [msg] },
                  ts: msg.ts ?? new Date().toISOString(),
                });
              }
            }
          } catch {
            // transcript might not exist yet
          }
        }
      })
      .catch(() => {
        // Backend not available, show empty state
        setBackendAvailable(false);
        setSessions(mockSessions);
        setActiveId(mockSessions[0].id);
      });
  }, [store]);

  const handleWSEvent = useCallback((event: WSEvent, runId: string) => {
    store.dispatch(runId, event);
  }, [store]);

  useRunSocket(liveRunId, handleWSEvent);

  const liveSession = liveRunId ? storeState.sessions.get(liveRunId) : undefined;
  const streamRevision = liveSession
    ? [
        liveSession.transcript.length,
        liveSession.run.status,
        Array.isArray(liveSession.run.research_findings)
          ? liveSession.run.research_findings.length
          : 0,
        liveSession.streams.size,
        liveSession.agents.map((a) => `${a.id}:${a.status}:${a.tool_calls}`).join("|"),
        liveSession.researchAgents.length,
      ].join(":")
    : "";

  const activeSession = useMemo(() => {
    if (liveRunId && storeState.sessions.has(liveRunId)) {
      const base = sessions.find((s) => s.id === liveRunId);
      const cards = buildCardsFromStore(store, liveRunId);
      const runState = storeState.sessions.get(liveRunId)!;
      return {
        id: liveRunId,
        name: base?.name ?? runState.run.question.slice(0, 40),
        date: base?.date ?? "",
        status: runState.run.status,
        runId: liveRunId,
        cards,
      } as Session;
    }
    return sessions.find((s) => s.id === activeId) ?? sessions[0] ?? {
      id: "", name: "No sessions", date: "", status: "idle" as const, cards: [],
    };
  }, [liveRunId, storeState, sessions, activeId, store, streamRevision]);

  const simCard = activeSession?.cards?.find((c) => c.type === "simulation");
  const hasSim = !!simCard;

  // Get live streams for sim rendering
  const liveStreams = useMemo(() => {
    if (!liveRunId) return new Map<string, LiveStream>();
    return storeState.sessions.get(liveRunId)?.streams ?? new Map();
  }, [liveRunId, storeState]);

  const handleAddWindow = useCallback(() => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeId) return s;
        return {
          ...s,
          cards: s.cards.map((c) => {
            if (c.type !== "simulation") return c;
            const content = c.content as SimCardType;
            if (content.windowCount >= content.maxWindows) return c;
            return {
              ...c,
              content: { ...content, windowCount: content.windowCount + 1 },
            };
          }),
        };
      }),
    );
  }, [activeId]);

  const handleNewSession = useCallback(
    async (config: { question: string; engineer_timeout: number; scientist_timeout: number }) => {
      const { question, engineer_timeout, scientist_timeout } = config;
      if (backendAvailable) {
        try {
          const res = await createRun(question, engineer_timeout, scientist_timeout, (config as RunConfig).model);
          const newSession = runToSession(res.run);
          store.handleSnapshot(res.run.id, res);
          setSessions((prev) => [newSession, ...prev]);
          setActiveId(res.run.id);
          setLiveRunId(res.run.id);
          return;
        } catch {
          // fall through to mock
        }
      }
      // Offline / mock mode
      const newSession: Session = {
        id: `s${Date.now()}`,
        name: question.length > 40 ? question.slice(0, 40) + "..." : question,
        date: new Date().toLocaleDateString("en", { month: "short", day: "numeric" }),
        status: "idle",
        cards: [
          {
            id: "c-user",
            type: "user",
            timestamp: new Date().toLocaleTimeString("en", { hour: "numeric", minute: "2-digit" }),
            content: { message: question },
          },
        ],
      };
      setSessions((prev) => [newSession, ...prev]);
      setActiveId(newSession.id);
      setLiveRunId(null);
    },
    [backendAvailable, store],
  );

  const handleSelectSession = useCallback(
    async (id: string) => {
      setActiveId(id);
      const session = sessions.find((s) => s.id === id);
      const runId = session?.runId ?? null;
      setLiveRunId(runId);
      // Load full state + transcript for this run
      if (runId && backendAvailable) {
        try {
          const full = await getRun(runId);
          store.handleSnapshot(runId, full);
          const transcript = await getTranscript(runId);
          for (const [agentId, data] of Object.entries(transcript)) {
            for (const msg of data.messages) {
              store.dispatch(runId, {
                type: "transcript",
                data: { agent_id: agentId, messages: [msg] },
                ts: msg.ts ?? new Date().toISOString(),
              });
            }
          }
        } catch {
          // ok if transcript doesn't exist
        }
      }
    },
    [sessions, backendAvailable, store],
  );

  const handleNewClick = useCallback(() => {
    // Just focus the input — actual creation happens on send
    const emptySession: Session = {
      id: `s${Date.now()}`,
      name: "New Session",
      date: new Date().toLocaleDateString("en", { month: "short", day: "numeric" }),
      status: "idle",
      cards: [],
    };
    setSessions((prev) => [emptySession, ...prev]);
    setActiveId(emptySession.id);
    setLiveRunId(null);
  }, []);

  return (
    <div className="h-full flex">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={handleSelectSession}
        onNew={handleNewClick}
      />
      <ChatView
        session={activeSession}
        hasSim={hasSim}
        onAddWindow={handleAddWindow}
        onSend={handleNewSession}
        liveStreams={liveStreams}
        liveRevision={streamRevision}
      />
    </div>
  );
}
