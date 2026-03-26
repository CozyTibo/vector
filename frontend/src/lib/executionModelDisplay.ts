/**
 * Human-readable labels for the execution-graph debug UI (presentation only).
 */

export const UI_TAB_LABELS = {
  artifacts: "Work Objects",
  actors: "People",
  relationships: "Connections",
  xrefs: "External IDs",
  graph: "Graph",
  status: "Pipeline Status",
} as const;

/** Backend artifact_kind ids (seeded). */
export const ARTIFACT_KIND_ID = {
  repository: 1,
  trackable_unit: 2,
  changeset: 3,
  revision: 4,
} as const;

export function workObjectTypeLabel(kind: string): string {
  switch (kind) {
    case "repository":
      return "Repository";
    case "trackable_unit":
      return "Issue";
    case "changeset":
      return "Pull request";
    case "revision":
      return "Commit";
    default:
      return kind;
  }
}

/**
 * Single-line label for work objects (list, detail title, graph).
 * Prefixes: repo / PR / commit / issue — …
 */
export function formatArtifactListLine(row: {
  artifact_kind_id?: number | null;
  title?: string | null;
  summary?: string | null;
}): string {
  const tid = row.artifact_kind_id ?? undefined;
  const title = row.title?.trim() ?? "";
  const summary = row.summary?.trim() ?? "";
  switch (tid) {
    case ARTIFACT_KIND_ID.repository:
      return title ? `repo ${title}` : "repo —";
    case ARTIFACT_KIND_ID.trackable_unit:
      return title ? `issue — ${title}` : "issue —";
    case ARTIFACT_KIND_ID.changeset:
      return title ? `PR — ${title}` : "PR —";
    case ARTIFACT_KIND_ID.revision:
      if (title && summary) {
        return `commit ${title} — ${summary}`;
      }
      if (title) {
        return title;
      }
      return "—";
    default:
      return title || "—";
  }
}

/** @deprecated alias — use {@link formatArtifactListLine} */
export function formatArtifactPrimaryLabel(row: {
  artifact_kind_id?: number | null;
  title?: string | null;
  summary?: string | null;
}): string {
  return formatArtifactListLine(row);
}

export function entityRoleLabel(type: string): string {
  if (type === "artifact") {
    return "Work object";
  }
  if (type === "actor") {
    return "Person";
  }
  return type;
}

/** Show backend relation_kind names as-is (authored_by, associated_with). */
export function relationKindRaw(kind: string): string {
  return kind;
}

export function graphEdgeLabelRaw(relationKind: string): string {
  return relationKind;
}

/** Graph node label from subgraph payload (title + kind). */
export function graphNodeDisplayLabel(n: {
  node_type: "artifact" | "actor";
  artifact_kind?: string | null;
  label?: string | null;
}): string {
  const raw = n.label?.trim() ?? "";
  if (n.node_type === "actor") {
    return raw || "Person";
  }
  // API may send fully formatted debug labels (same as relationship endpoints).
  if (
    raw &&
    (raw.startsWith("commit ") ||
      raw.startsWith("repo ") ||
      raw.startsWith("PR —") ||
      raw.startsWith("issue —"))
  ) {
    return raw;
  }
  const ak = n.artifact_kind;
  if (ak === "revision") {
    return raw ? `commit ${raw}` : "commit";
  }
  if (ak === "repository") {
    return raw ? `repo ${raw}` : "repo";
  }
  if (ak === "changeset") {
    return raw ? `PR — ${raw}` : "PR";
  }
  if (ak === "trackable_unit") {
    return raw ? `issue — ${raw}` : "issue";
  }
  return raw || "Work object";
}
