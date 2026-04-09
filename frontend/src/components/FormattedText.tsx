"use client";

import { Fragment } from "react";

function formatInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    const m = p.match(/^\*\*(.+)\*\*$/);
    if (m) {
      return (
        <strong key={i} className="font-semibold text-text-primary">
          {m[1]}
        </strong>
      );
    }
    return <Fragment key={i}>{p}</Fragment>;
  });
}

export function FormattedProse({ text }: { text: string }) {
  const paragraphs = text.split(/\n\n+/);
  return (
    <div className="text-[13px] text-text-secondary leading-relaxed space-y-3">
      {paragraphs.map((para, pi) => (
        <div key={pi} className="space-y-1.5">
          {para.split("\n").map((line, li) => {
            const t = line.trim();
            if (!t) return null;
            if (t.startsWith("## ")) {
              return (
                <h4
                  key={li}
                  className="text-[12px] font-semibold text-text-primary pt-1 border-b border-border-light pb-0.5"
                >
                  {formatInline(t.slice(3))}
                </h4>
              );
            }
            if (t.startsWith("### ")) {
              return (
                <h5 key={li} className="text-[12px] font-medium text-text-primary">
                  {formatInline(t.slice(4))}
                </h5>
              );
            }
            if (/^[-*]\s+/.test(t)) {
              return (
                <p key={li} className="pl-3 border-l border-border-light text-text-secondary">
                  {formatInline(t.replace(/^[-*]\s+/, ""))}
                </p>
              );
            }
            return (
              <p key={li} className="leading-relaxed">
                {formatInline(t)}
              </p>
            );
          })}
        </div>
      ))}
    </div>
  );
}
