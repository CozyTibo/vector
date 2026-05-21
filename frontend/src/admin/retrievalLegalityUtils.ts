/** Minimal retrieval legality helpers (admin revamp — catalog surfaces removed). */

export function normalizeRetrievalLegalityClassNames(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map((x) => String(x)).filter(Boolean);
  }
  if (raw && typeof raw === "object") {
    return Object.keys(raw as Record<string, unknown>).filter(Boolean);
  }
  return [];
}
