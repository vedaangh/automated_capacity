"use client";

import type { UserCard as UserCardType } from "@/lib/types";

export default function UserCardView({ content }: { content: UserCardType }) {
  return (
    <div className="animate-fade-in">
      <p className="text-[14.5px] text-text-primary leading-relaxed">
        {content.message}
      </p>
      {content.budget && (
        <span className="inline-block mt-2 px-2 py-0.5 text-[10px] text-text-muted bg-text-primary/5 rounded tracking-wide uppercase">
          {content.budget}
        </span>
      )}
    </div>
  );
}
