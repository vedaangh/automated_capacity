"use client";

import type { EngineeringCard as EngineeringCardType } from "@/lib/types";
import ExpandableSection from "../ExpandableSection";

export default function EngineeringCardView({
  content,
}: {
  content: EngineeringCardType;
}) {
  return (
    <div className="animate-fade-in">
      <p className="text-[13.5px] text-text-primary leading-relaxed">{content.summary}</p>

      {content.simSpec && (
        <div className="mt-1.5 text-[10px] font-mono text-text-muted">
          {content.simSpec.name} &middot; {content.simSpec.direction} {content.simSpec.metric} &middot; {content.simSpec.timeoutSeconds}s budget
        </div>
      )}

      <ExpandableSection label="Build log">
        <div className="font-mono text-[11px] text-text-muted leading-[1.7]">
          {content.trace.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      </ExpandableSection>
    </div>
  );
}
