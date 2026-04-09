"use client";

import type { ExperimentCard as ExperimentCardType, Experiment } from "@/lib/types";

function formatLine(exp: Experiment): string {
  const id = `#${exp.id}`.padEnd(4);
  const status = exp.status.toUpperCase().padEnd(10);
  const metric = exp.metric != null ? String(exp.metric).padEnd(8) : "—".padEnd(8);

  const delta =
    exp.status === "kept" && exp.prevMetric != null && exp.metric != null
      ? ` (${exp.metric - exp.prevMetric > 0 ? "+" : ""}${exp.metric - exp.prevMetric})`
      : "";

  const progress =
    exp.status === "running" && exp.elapsed != null && exp.budget != null
      ? ` [${exp.elapsed}s/${exp.budget}s]`
      : "";

  return `${id} ${status} ${metric} ${exp.description}${delta}${progress}`;
}

function statusColor(status: string): string {
  switch (status) {
    case "kept": return "text-accent-green";
    case "crash": return "text-accent-red";
    case "running": return "text-accent-blue";
    default: return "text-text-muted";
  }
}

export default function ExperimentCardView({ content }: { content: ExperimentCardType }) {
  return (
    <div className="animate-fade-in font-mono text-[11.5px] leading-[1.8]">
      {content.experiments.map((exp) => (
        <div key={exp.id} className={statusColor(exp.status)}>
          {formatLine(exp)}
        </div>
      ))}
    </div>
  );
}
