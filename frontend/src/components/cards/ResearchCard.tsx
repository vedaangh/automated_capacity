"use client";

import type { ResearchCard as ResearchCardType } from "@/lib/types";
import ExpandableSection from "../ExpandableSection";
import { FormattedProse } from "../FormattedText";
import { sanitizeDisplayText } from "@/lib/formatDisplay";

export default function ResearchCardView({ content }: { content: ResearchCardType }) {
  return (
    <div className="animate-fade-in rounded-lg border border-border-light bg-bg-secondary/30 px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.12em] text-text-muted mb-2">Research</div>
      <p className="text-[13.5px] text-text-primary leading-relaxed mb-2">{content.summary}</p>

      <ExpandableSection label={`${content.agents.length} research agents`} defaultOpen={false}>
        <div className="space-y-4">
          {content.agents.map((agent) => (
            <div key={agent.name}>
              <div className="flex flex-col gap-0.5 mb-1">
                <span className="text-[12.5px] font-medium text-text-primary">{agent.name}</span>
                <span className="text-[10px] font-mono text-text-muted break-all">{agent.query}</span>
              </div>
              <div className="text-[12px] text-text-secondary leading-relaxed">
                <FormattedProse text={sanitizeDisplayText(agent.findings, 16000)} />
              </div>
            </div>
          ))}
        </div>
      </ExpandableSection>
    </div>
  );
}
