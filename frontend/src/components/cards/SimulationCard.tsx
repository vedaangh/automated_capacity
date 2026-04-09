"use client";

import type { SimulationCard as SimulationCardType } from "@/lib/types";

const gridClass: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-2",
  4: "grid-cols-2",
};

export default function SimulationCardView({
  content,
  onAddWindow,
  expanded,
}: {
  content: SimulationCardType;
  onAddWindow: () => void;
  expanded: boolean;
}) {
  const windows = Array.from({ length: content.windowCount }, (_, i) => i);

  return (
    <div className={`flex flex-col ${expanded ? "flex-1" : ""}`}>
      <div className={`grid ${gridClass[content.windowCount]} gap-1 ${expanded ? "flex-1" : ""}`}>
        {windows.map((i) => (
          <div
            key={i}
            className={`bg-[#111] flex items-center justify-center ${
              expanded ? "min-h-0" : "h-48"
            } ${content.windowCount === 3 && i === 0 ? "col-span-2" : ""}`}
          >
            <span className="text-[10px] text-white/25 font-mono">
              {content.connected ? "awaiting stream" : "not connected"}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3">
        {content.windowCount < content.maxWindows && (
          <button
            onClick={onAddWindow}
            className="text-[11px] text-text-muted hover:text-text-primary transition-colors cursor-pointer"
          >
            + add view
          </button>
        )}
      </div>
    </div>
  );
}
