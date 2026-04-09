"use client";

import { useRef, useEffect } from "react";
import type { Session, Card, SimulationCard as SimCardType } from "@/lib/types";
import type { LiveStream } from "@/lib/store";
import ChatInput from "./ChatInput";
import UserCardView from "./cards/UserCard";
import ResearchCardView from "./cards/ResearchCard";
import EngineeringCardView from "./cards/EngineeringCard";
import SimulationCardView from "./cards/SimulationCard";
import ExperimentCardView from "./cards/ExperimentCard";
import StreamRenderer from "./cards/StreamRenderer";
import type {
  UserCard,
  ResearchCard,
  EngineeringCard,
  ExperimentCard,
  StatusCard,
  FindingsCard,
  ErrorCard,
} from "@/lib/types";

const typeLabel: Record<string, string> = {
  user: "Prompt",
  research: "Research",
  engineering: "Engineering",
  experiment: "Experiments",
  status: "Status",
  findings: "Findings",
  error: "Error",
  simulation: "",
};

function StatusCardView({ content }: { content: StatusCard }) {
  return (
    <div className="animate-fade-in">
      <div className="flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
        <span className="text-[13px] text-text-secondary">{content.message}</span>
      </div>
    </div>
  );
}

function FindingsCardView({ content }: { content: FindingsCard }) {
  return (
    <div className="animate-fade-in">
      <p className="text-[13.5px] text-text-primary leading-relaxed whitespace-pre-wrap">{content.text}</p>
    </div>
  );
}

function ErrorCardView({ content }: { content: ErrorCard }) {
  return (
    <div className="animate-fade-in">
      <p className="text-[13px] text-accent-red">{content.message}</p>
    </div>
  );
}

function CardContent({
  card,
  onAddWindow,
}: {
  card: Card;
  onAddWindow: () => void;
}) {
  switch (card.type) {
    case "user":
      return <UserCardView content={card.content as UserCard} />;
    case "research":
      return <ResearchCardView content={card.content as ResearchCard} />;
    case "engineering":
      return <EngineeringCardView content={card.content as EngineeringCard} />;
    case "simulation":
      return null;
    case "experiment":
      return <ExperimentCardView content={card.content as ExperimentCard} />;
    case "status":
      return <StatusCardView content={card.content as StatusCard} />;
    case "findings":
      return <FindingsCardView content={card.content as FindingsCard} />;
    case "error":
      return <ErrorCardView content={card.content as ErrorCard} />;
    default:
      return null;
  }
}

function TimelinePanel({
  cards,
  onAddWindow,
}: {
  cards: Card[];
  onAddWindow: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const panelCards = cards.filter((c) => c.type !== "simulation");

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [cards.length]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5">
      <div className="space-y-6">
        {panelCards.map((card, i) => (
          <div key={card.id} className="animate-fade-in">
            {card.timestamp && (
              <div className="flex items-baseline gap-3 mb-1.5">
                <span className="text-[10px] font-mono text-text-muted tabular-nums">{card.timestamp}</span>
                {typeLabel[card.type] && (
                  <span className="text-[10px] text-text-muted uppercase tracking-[0.1em]">
                    {typeLabel[card.type]}
                  </span>
                )}
              </div>
            )}
            <CardContent card={card} onAddWindow={onAddWindow} />
            {i < panelCards.length - 1 && (
              <div className="mt-6 border-b border-border" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ChatView({
  session,
  hasSim,
  onAddWindow,
  onSend,
  liveStreams,
}: {
  session: Session;
  hasSim: boolean;
  onAddWindow: () => void;
  onSend: (question: string) => void;
  liveStreams?: Map<string, LiveStream>;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputDisabled = session.cards.length > 0 && session.status !== "idle";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [session.cards.length]);

  const simCard = session.cards.find((c) => c.type === "simulation");
  const simContent = simCard?.content as SimCardType | undefined;

  if (hasSim && simContent) {
    // Gather streams for the sim windows
    const streamEntries = liveStreams
      ? Array.from(liveStreams.values()).slice(0, simContent.windowCount)
      : [];

    return (
      <div className="flex-1 flex min-w-0">
        <div className="flex-1 flex flex-col p-5 min-w-0 animate-fade-in">
          <div className="flex items-baseline gap-3 mb-4">
            <span className="text-[10px] text-text-muted uppercase tracking-[0.1em]">Simulation</span>
            <span className="text-[10px] font-mono text-text-muted">
              {simContent.windowCount} view{simContent.windowCount !== 1 ? "s" : ""}
            </span>
          </div>
          {streamEntries.length > 0 ? (
            <StreamRenderer streams={streamEntries} onAddWindow={onAddWindow} maxWindows={simContent.maxWindows} />
          ) : (
            <SimulationCardView content={simContent} onAddWindow={onAddWindow} expanded />
          )}
        </div>

        <div className="w-[360px] shrink-0 bg-bg-secondary flex flex-col animate-slide-in-right">
          <div className="px-5 pt-5 pb-4">
            <span className="text-[13px] text-text-primary">{session.name}</span>
          </div>
          <TimelinePanel cards={session.cards} onAddWindow={onAddWindow} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-2xl mx-auto px-6 py-10 space-y-5">
          {session.cards.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center animate-hero-reveal">
              <h2 className="text-[1.4rem] text-text-primary mb-2 leading-tight">
                What should we investigate?
              </h2>
              <p className="text-[13px] text-text-muted max-w-sm leading-relaxed">
                Describe a problem and the agent will build a simulation
                and run experiments autonomously.
              </p>
            </div>
          )}

          {session.cards.map((card) => (
            <div key={card.id}>
              <CardContent card={card} onAddWindow={onAddWindow} />
            </div>
          ))}
        </div>
      </div>
      <ChatInput onSend={onSend} disabled={inputDisabled} />
    </div>
  );
}
