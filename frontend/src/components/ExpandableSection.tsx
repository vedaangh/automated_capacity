"use client";

import { useState } from "react";

export default function ExpandableSection({
  label,
  children,
  defaultOpen = false,
  variant = "scroll",
}: {
  label: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  variant?: "scroll" | "plain";
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="mt-1.5">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 text-[12px] text-text-muted hover:text-text-secondary transition-colors cursor-pointer py-0.5 text-left"
      >
        <svg
          width="8"
          height="8"
          viewBox="0 0 8 8"
          className={`shrink-0 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          fill="none"
        >
          <path d="M2 1L6 4L2 7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>{label}</span>
      </button>
      {open &&
        (variant === "scroll" ? (
          <div className="mt-2 max-h-[min(52vh,560px)] overflow-y-auto rounded-md border border-border/50 bg-bg-tertiary/40 px-3 py-2.5">
            {children}
          </div>
        ) : (
          <div className="mt-2">{children}</div>
        ))}
    </div>
  );
}
