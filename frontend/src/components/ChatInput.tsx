"use client";

import { useState } from "react";

export interface RunConfig {
  question: string;
  engineer_timeout: number;
  scientist_timeout: number;
  model: string;
}

const TIMEOUT_PRESETS = [
  { label: "Low", minutes: 1 },
  { label: "Medium", minutes: 2 },
  { label: "High", minutes: 5 },
  { label: "Max", minutes: 10 },
  { label: "Ultra-Max", minutes: 20 },
] as const;

const MODEL_PRESETS = [
  { label: "Haiku", id: "us.anthropic.claude-haiku-4-5-20251001-v1:0" },
  { label: "Sonnet", id: "us.anthropic.claude-sonnet-4-20250514-v1:0" },
  { label: "Opus", id: "us.anthropic.claude-opus-4-6-v1" },
] as const;

export default function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (config: RunConfig) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const [selectedPreset, setSelectedPreset] = useState(2); // High (5 min)
  const [selectedModel, setSelectedModel] = useState(0);   // Haiku

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    const minutes = TIMEOUT_PRESETS[selectedPreset].minutes;
    onSend({
      question: value.trim(),
      engineer_timeout: minutes * 60,
      scientist_timeout: minutes * 60,
      model: MODEL_PRESETS[selectedModel].id,
    });
    setValue("");
  };

  return (
    <div
      className={`transition-opacity duration-500 ${
        disabled ? "opacity-35 pointer-events-none" : "opacity-100"
      }`}
    >
      <div className="max-w-2xl mx-auto px-5 pb-8 pt-3">
        {disabled && (
          <p className="text-[11px] text-text-muted text-center mb-3 tracking-wide">
            Agent running autonomously
          </p>
        )}

        <div className="flex items-center gap-4 mb-2 px-1">
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-text-muted uppercase tracking-wider mr-1">Budget</span>
            {TIMEOUT_PRESETS.map((preset, i) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => setSelectedPreset(i)}
                disabled={disabled}
                className={`px-2 py-0.5 text-[10px] rounded transition-all cursor-pointer ${
                  i === selectedPreset
                    ? "bg-text-primary/10 text-text-primary"
                    : "text-text-muted hover:text-text-primary hover:bg-text-primary/5"
                }`}
              >
                {preset.label}
                <span className="ml-0.5 opacity-50">{preset.minutes}m</span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1">
            <span className="text-[10px] text-text-muted uppercase tracking-wider mr-1">Model</span>
            {MODEL_PRESETS.map((model, i) => (
              <button
                key={model.label}
                type="button"
                onClick={() => setSelectedModel(i)}
                disabled={disabled}
                className={`px-2 py-0.5 text-[10px] rounded transition-all cursor-pointer ${
                  i === selectedModel
                    ? "bg-text-primary/10 text-text-primary"
                    : "text-text-muted hover:text-text-primary hover:bg-text-primary/5"
                }`}
              >
                {model.label}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-bg-tertiary px-4 border-b border-text-primary/20 focus-within:border-text-primary transition-colors duration-200">
          <div className="flex items-end">
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Describe a problem to investigate..."
              rows={1}
              className="flex-1 bg-transparent py-3 text-[14px] text-text-primary placeholder:text-text-muted resize-none outline-none min-h-[40px] max-h-[160px] leading-relaxed"
              style={{ fieldSizing: "content" } as React.CSSProperties}
              disabled={disabled}
            />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={disabled || !value.trim()}
              className="py-3 pl-4 text-[13px] text-text-muted hover:text-text-primary disabled:opacity-20 transition-colors cursor-pointer"
              aria-label="Send"
            >
              &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
