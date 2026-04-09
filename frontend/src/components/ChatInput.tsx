"use client";

import { useState } from "react";

export default function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
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
