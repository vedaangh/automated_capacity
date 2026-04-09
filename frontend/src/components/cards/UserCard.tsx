"use client";

import type { UserCard as UserCardType } from "@/lib/types";

export default function UserCardView({ content }: { content: UserCardType }) {
  return (
    <div className="animate-fade-in">
      <p className="text-[14.5px] text-text-primary leading-relaxed">
        {content.message}
      </p>
    </div>
  );
}
