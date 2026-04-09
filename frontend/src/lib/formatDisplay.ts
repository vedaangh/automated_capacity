export function stripHtml(s: string): string {
  return s
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function sanitizeDisplayText(s: string, maxLen = 12000): string {
  const t = stripHtml(s);
  if (t.length > maxLen) return `${t.slice(0, maxLen)}\n\n[truncated]`;
  return t;
}
