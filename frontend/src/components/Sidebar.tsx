"use client";

import type { Session } from "@/lib/types";

export default function Sidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
}: {
  sessions: Session[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  return (
    <aside className="w-[260px] shrink-0 h-full bg-bg-secondary flex flex-col">
      <div className="px-5 pt-6 pb-5">
        <button
          type="button"
          onClick={onNew}
          className="text-[11px] font-semibold text-text-muted tracking-[0.12em] uppercase hover:text-text-primary transition-colors cursor-pointer"
        >
          Automated Capacity
        </button>
      </div>

      <div className="px-4 pb-4">
        <button
          type="button"
          onClick={onNew}
          className="text-[13px] text-text-muted hover:text-text-primary transition-colors cursor-pointer"
        >
          + New
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        {sessions.map((s) => {
          const active = s.id === activeId;
          return (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`w-full text-left px-3 py-2.5 transition-colors duration-100 cursor-pointer group flex items-center justify-between gap-3 ${
                active ? "bg-bg-primary" : "hover:bg-bg-primary"
              }`}
            >
              <span
                className={`text-[13px] truncate ${
                  active ? "text-text-primary" : "text-text-secondary group-hover:text-text-primary"
                }`}
              >
                {s.name}
              </span>
              <span className="text-[11px] text-text-muted shrink-0">{s.date}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
