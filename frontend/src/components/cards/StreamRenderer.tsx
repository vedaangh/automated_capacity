"use client";

import type { LiveStream } from "@/lib/store";

const gridClass: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-2",
  4: "grid-cols-2",
};

function TextLogStream({ stream }: { stream: LiveStream }) {
  const lines = stream.data
    .flat()
    .map((p) => {
      const vals = Object.values(p);
      return vals.map(String).join(" ");
    })
    .slice(-100);

  return (
    <div className="bg-[#111] text-[#ccc] font-mono text-[11px] leading-[1.6] p-3 overflow-y-auto h-full">
      {lines.length === 0 ? (
        <span className="text-white/25">awaiting data...</span>
      ) : (
        lines.map((line, i) => <div key={i}>{line}</div>)
      )}
    </div>
  );
}

function LineChartStream({ stream }: { stream: LiveStream }) {
  const points = stream.data.flat();
  if (points.length === 0) {
    return (
      <div className="bg-[#111] flex items-center justify-center h-full">
        <span className="text-[10px] text-white/25 font-mono">awaiting data...</span>
      </div>
    );
  }

  // Simple ASCII-ish chart — get the y-key from config or first numeric key
  const config = stream.spec.config;
  const yKeys = (config.y as string[]) ?? Object.keys(points[0]).filter((k) => k !== "step" && k !== "x" && typeof points[0][k] === "number");
  const xKey = (config.x as string) ?? "step";

  const yKey = yKeys[0] ?? Object.keys(points[0])[1] ?? "y";
  const values = points.map((p) => Number(p[yKey]) || 0);
  const maxVal = Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  // Render as a simple SVG sparkline
  const w = 400;
  const h = 120;
  const pathD = values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * w;
      const y = h - ((v - minVal) / range) * (h - 10) - 5;
      return `${i === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");

  return (
    <div className="bg-[#111] p-3 h-full flex flex-col">
      <div className="text-[10px] text-white/40 font-mono mb-1">
        {stream.spec.title} &middot; {yKey} &middot; {values.length} pts
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="flex-1 w-full" preserveAspectRatio="none">
        <path d={pathD} fill="none" stroke="#4ade80" strokeWidth="1.5" />
      </svg>
      <div className="flex justify-between text-[9px] font-mono text-white/30 mt-1">
        <span>{minVal.toFixed(2)}</span>
        <span>{maxVal.toFixed(2)}</span>
      </div>
    </div>
  );
}

function MetricCardStream({ stream }: { stream: LiveStream }) {
  const points = stream.data.flat();
  const latest = points[points.length - 1];

  return (
    <div className="bg-[#111] p-4 h-full flex flex-col justify-center">
      <div className="text-[10px] text-white/40 font-mono mb-1">{stream.spec.title}</div>
      {latest ? (
        <div className="text-[24px] font-mono text-white/90 tabular-nums">
          {Object.entries(latest)
            .map(([k, v]) => `${k}: ${typeof v === "number" ? v.toFixed(4) : v}`)
            .join("  ")}
        </div>
      ) : (
        <span className="text-[10px] text-white/25 font-mono">awaiting data...</span>
      )}
    </div>
  );
}

function TableStream({ stream }: { stream: LiveStream }) {
  const points = stream.data.flat();
  if (points.length === 0) {
    return (
      <div className="bg-[#111] flex items-center justify-center h-full">
        <span className="text-[10px] text-white/25 font-mono">awaiting data...</span>
      </div>
    );
  }

  const cols = Object.keys(points[0]);

  return (
    <div className="bg-[#111] text-white/80 font-mono text-[10px] p-2 overflow-auto h-full">
      <table className="w-full">
        <thead>
          <tr className="text-white/40 border-b border-white/10">
            {cols.map((c) => (
              <th key={c} className="text-left py-1 px-1.5 font-normal">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {points.slice(-50).map((row, i) => (
            <tr key={i} className="border-b border-white/5">
              {cols.map((c) => (
                <td key={c} className="py-0.5 px-1.5 tabular-nums">{String(row[c] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GenericStream({ stream }: { stream: LiveStream }) {
  return (
    <div className="bg-[#111] flex items-center justify-center h-full">
      <div className="text-center">
        <div className="text-[10px] text-white/40 font-mono mb-1">{stream.spec.title}</div>
        <span className="text-[10px] text-white/25 font-mono">
          {stream.spec.component_type} &middot; {stream.data.flat().length} points
        </span>
      </div>
    </div>
  );
}

function StreamWindow({ stream }: { stream: LiveStream }) {
  switch (stream.spec.component_type) {
    case "text_log":
      return <TextLogStream stream={stream} />;
    case "line_chart":
    case "scatter_plot":
      return <LineChartStream stream={stream} />;
    case "metric_card":
      return <MetricCardStream stream={stream} />;
    case "table":
      return <TableStream stream={stream} />;
    default:
      return <GenericStream stream={stream} />;
  }
}

export default function StreamRenderer({
  streams,
  onAddWindow,
  maxWindows,
}: {
  streams: LiveStream[];
  onAddWindow: () => void;
  maxWindows: number;
}) {
  const count = streams.length;

  return (
    <div className="flex flex-col flex-1">
      <div className={`grid ${gridClass[Math.min(count, 4)]} gap-1 flex-1`}>
        {streams.slice(0, 4).map((stream) => (
          <div
            key={stream.spec.id}
            className={`min-h-0 ${count === 3 && stream === streams[0] ? "col-span-2" : ""}`}
          >
            <StreamWindow stream={stream} />
          </div>
        ))}
      </div>
      {count < maxWindows && (
        <div className="mt-3">
          <button
            onClick={onAddWindow}
            className="text-[11px] text-text-muted hover:text-text-primary transition-colors cursor-pointer"
          >
            + add view
          </button>
        </div>
      )}
    </div>
  );
}
