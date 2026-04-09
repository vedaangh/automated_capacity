"use client";

import type { EngineeringCard as EngineeringCardType } from "@/lib/types";
import ExpandableSection from "../ExpandableSection";
import { FormattedProse } from "../FormattedText";

export default function EngineeringCardView({
  content,
}: {
  content: EngineeringCardType;
}) {
  const thinkingText =
    content.thinking && content.thinking.length > 0
      ? content.thinking.join("\n\n")
      : "";

  return (
    <div className="animate-fade-in rounded-lg border border-border-light bg-bg-secondary/40 px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.12em] text-text-muted mb-1">Engineer</div>
      <p className="text-[13.5px] text-text-primary leading-relaxed">{content.summary}</p>

      {content.simSpec && (
        <div className="mt-1.5 text-[10px] font-mono text-text-muted">
          {content.simSpec.name} &middot; {content.simSpec.direction} {content.simSpec.metric} &middot;{" "}
          {content.simSpec.timeoutSeconds}s budget
        </div>
      )}

      {thinkingText.length > 0 && (
        <ExpandableSection label="Thinking" defaultOpen={false}>
          <FormattedProse text={thinkingText} />
        </ExpandableSection>
      )}

      <ExpandableSection label="Build log" defaultOpen={false}>
        <div className="font-mono text-[11px] text-text-muted leading-[1.7] whitespace-pre-wrap break-all">
          {content.trace.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      </ExpandableSection>
    </div>
  );
}
