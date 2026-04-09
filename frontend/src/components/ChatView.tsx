"use client";

import { useRef, useEffect } from "react";
import type { Session, Card, SimulationCard as SimCardType } from "@/lib/types";
import ChatInput from "./ChatInput";
import UserCardView from "./cards/UserCard";
import ResearchCardView from "./cards/ResearchCard";
import EngineeringCardView from "./cards/EngineeringCard";
import SimulationCardView from "./cards/SimulationCard";
import ExperimentCardView from "./cards/ExperimentCard";
import type {
  UserCard,
  ResearchCard,
  EngineeringCard,
  ExperimentCard,
} from "@/lib/types";

const typeLabel: Record<string, string> = {
  user: "Prompt",
  research: "Research",
  engineering: "Engineering",
  experiment: "Experiments",
};

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
            <div className="flex items-baseline gap-3 mb-1.5">
              <span className="text-[10px] font-mono text-text-muted tabular-nums">{card.timestamp}</span>
              {typeLabel[card.type] && (
                <span className="text-[10px] text-text-muted uppercase tracking-[0.1em]">
                  {typeLabel[card.type]}
                </span>
              )}
            </div>
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
}: {
  session: Session;
  hasSim: boolean;
  onAddWindow: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputDisabled = session.cards.some(
    (c) => c.type === "engineering" || c.type === "experiment"
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [session.cards.length]);

  const simCard = session.cards.find((c) => c.type === "simulation");
  const simContent = simCard?.content as SimCardType | undefined;

  if (hasSim && simContent) {
    return (
      <div className="flex-1 flex min-w-0">
        <div className="flex-1 flex flex-col p-5 min-w-0 animate-fade-in">
          <div className="flex items-baseline gap-3 mb-4">
            <span className="text-[10px] text-text-muted uppercase tracking-[0.1em]">Simulation</span>
            <span className="text-[10px] font-mono text-text-muted">
              {simContent.windowCount} view{simContent.windowCount !== 1 ? "s" : ""}
            </span>
          </div>
          <SimulationCardView content={simContent} onAddWindow={onAddWindow} expanded />
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
      <ChatInput onSend={() => {}} disabled={inputDisabled} />
    </div>
  );
}
