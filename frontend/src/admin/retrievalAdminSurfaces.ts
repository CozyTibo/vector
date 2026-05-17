/** Phase 07 Step 24 — SPA route registry for retrieval admin surfaces. */

export type RetrievalCatalogSurface = {
  title: string;
  description: string;
  endpoint: string;
};

export const RETRIEVAL_CATALOG_SURFACES: Record<string, RetrievalCatalogSurface> = {
  coverage: {
    title: "Coverage panel",
    description: "Eligible vs indexed vs replay-safe coverage.",
    endpoint: "/coverage",
  },
  policy: {
    title: "Policy digest inspector",
    description: "Active retrieval_policy_digest, caps, and query contract.",
    endpoint: "/legality",
  },
  provenance: {
    title: "Provenance inspector",
    description: "Per-hit upstream digests and evidence legality.",
    endpoint: "/provenance-inspector",
  },
  replay: {
    title: "Replay inspector",
    description: "Twin run diff and retrieval_query_replay_identity (W2).",
    endpoint: "/replay-inspector",
  },
  omissions: {
    title: "Omission explorer",
    description: "RD-* classes, counts, and upstream triggers.",
    endpoint: "/omission-explorer",
  },
  temporal: {
    title: "Temporal explorer",
    description: "t_as_of, windows, and epoch pins.",
    endpoint: "/temporal-explorer",
  },
  traversal: {
    title: "Traversal binding",
    description: "walk_id, hop coverage, epoch match.",
    endpoint: "/traversal-binding",
  },
  tcre: {
    title: "TCRE binding",
    description: "job id, chain id, chronology class.",
    endpoint: "/tcre-binding",
  },
  degradation: {
    title: "Degradation topology",
    description: "Rollup graph of RD-* and upstream propagation.",
    endpoint: "/degradation-topology",
  },
  readiness: {
    title: "Readiness economics",
    description: "Numeric readiness receipt (Step 25 when fully wired).",
    endpoint: "/readiness-economics",
  },
  index: {
    title: "Index materialization",
    description: "Index epochs and publish barrier catalog.",
    endpoint: "/index",
  },
};

export const RETRIEVAL_NAV_SECTIONS = [
  { key: "", label: "Overview", end: true as const },
  { key: "workflows", label: "Workflows", end: true as const },
  { key: "query", label: "Query debugger", end: true as const },
  { key: "audit", label: "Audit trail", end: true as const },
  { key: "coverage", label: "Coverage", end: true as const },
  { key: "policy", label: "Policy", end: true as const },
  { key: "provenance", label: "Provenance", end: true as const },
  { key: "replay", label: "Replay", end: true as const },
  { key: "omissions", label: "Omissions", end: true as const },
  { key: "temporal", label: "Temporal", end: true as const },
  { key: "lineage", label: "Lineage", end: true as const },
  { key: "traversal", label: "Traversal", end: true as const },
  { key: "tcre", label: "TCRE", end: true as const },
  { key: "degradation", label: "Degradation", end: true as const },
  { key: "legality", label: "Legality", end: true as const },
  { key: "readiness", label: "Readiness", end: true as const },
  { key: "index", label: "Index", end: true as const },
  { key: "control-plane", label: "Control plane", end: true as const },
  { key: "continuity", label: "Continuity", end: true as const },
  { key: "certification-pack", label: "Cert pack", end: true as const },
  { key: "program-closure", label: "Program closure", end: true as const },
] as const;

/** API returns ``legality_classes`` as strings or ``{ class, ordinal, ... }`` rows. */
export function normalizeRetrievalLegalityClassNames(legality_classes: unknown): string[] {
  if (!Array.isArray(legality_classes)) return [];
  return legality_classes.map((item) => {
    if (typeof item === "string") return item;
    if (item && typeof item === "object" && "class" in item) {
      return String((item as { class: unknown }).class);
    }
    return String(item);
  });
}
