"use client";

import { useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import ChatView from "@/components/ChatView";
import { mockSessions } from "@/lib/mock-data";
import type { Session, SimulationCard as SimCardType } from "@/lib/types";

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>(mockSessions);
  const [activeId, setActiveId] = useState(mockSessions[0].id);

  const activeSession = sessions.find((s) => s.id === activeId) ?? sessions[0];

  // Check if simulation card exists → triggers split layout
  const simCard = activeSession.cards.find((c) => c.type === "simulation");
  const hasSim = !!simCard;

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
      })
    );
  }, [activeId]);

  const handleNewSession = useCallback(() => {
    const newSession: Session = {
      id: `s${Date.now()}`,
      name: "New Session",
      date: "Apr 9",
      status: "idle",
      domain: "",
      cards: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveId(newSession.id);
  }, []);

  return (
    <div className="h-full flex">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewSession}
      />
      <ChatView
        session={activeSession}
        hasSim={hasSim}
        onAddWindow={handleAddWindow}
      />
    </div>
  );
}
