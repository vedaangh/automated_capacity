"use client";

import type { ResearchCard as ResearchCardType } from "@/lib/types";
import ExpandableSection from "../ExpandableSection";

export default function ResearchCardView({ content }: { content: ResearchCardType }) {
  return (
    <div className="animate-fade-in">
      <p className="text-[13.5px] text-text-primary leading-relaxed">{content.summary}</p>

      <ExpandableSection label={`${content.agents.length} research agents`}>
        <div className="space-y-4">
          {content.agents.map((agent) => (
            <div key={agent.name}>
              <div className="flex items-baseline gap-2 mb-0.5">
                <span className="text-[12.5px] font-medium text-text-primary">{agent.name}</span>
                <span className="text-[10px] font-mono text-text-muted">{agent.query}</span>
              </div>
              <p className="text-[12px] text-text-secondary leading-relaxed">{agent.findings}</p>
            </div>
          ))}
        </div>
      </ExpandableSection>
    </div>
  );
}
