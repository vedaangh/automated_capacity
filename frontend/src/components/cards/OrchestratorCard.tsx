"use client";

import type { OrchestratorCard as OrchestratorCardType } from "@/lib/types";
import { FormattedProse } from "../FormattedText";

export default function OrchestratorCardView({
  content,
}: {
  content: OrchestratorCardType;
}) {
  return (
    <div className="animate-fade-in border-l-2 border-accent-blue/35 pl-4 -ml-0.5">
      <FormattedProse text={content.thinking} />
    </div>
  );
}
