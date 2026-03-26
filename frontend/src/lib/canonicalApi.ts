/** Fetch helpers for /debug/canonical (Step 3 ontology debug). */

export function getApiBase(): string {
  return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, "");
}

export async function readErrorDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string | unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    /* ignore */
  }
  return `HTTP ${res.status}`;
}

export type Paginated<T> = {
  total: number;
  limit: number;
  offset: number;
  items: T[];
};

/** Seeded registry ids — see migration `20260324_0011_step3_canonical_ontology`. */
export const ARTIFACT_KIND_BY_ID: Record<number, string> = {
  1: "repository",
  2: "trackable_unit",
  3: "changeset",
  4: "revision",
};

export const RELATION_KIND_BY_ID: Record<number, string> = {
  1: "authored_by",
  2: "associated_with",
  3: "contains",
};

export function artifactKindName(id: number | null | undefined): string {
  if (id == null) {
    return "—";
  }
  return ARTIFACT_KIND_BY_ID[id] ?? String(id);
}

export function relationKindName(id: number | null | undefined): string {
  if (id == null) {
    return "—";
  }
  return RELATION_KIND_BY_ID[id] ?? String(id);
}

async function jsonFetch<T>(url: string): Promise<T> {
  const res = await fetch(url, { credentials: "include" });
  if (res.status === 401) {
    throw new Error("Not signed in");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<T>;
}

export async function fetchArtifactsPage(
  base: string,
  opts: { limit: number; offset: number; q?: string },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
  });
  if (opts.q?.trim()) {
    q.set("q", opts.q.trim());
  }
  return jsonFetch(`${base}/debug/canonical/artifacts?${q}`);
}

export async function fetchActorsPage(
  base: string,
  opts: { limit: number; offset: number; q?: string },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
  });
  if (opts.q?.trim()) {
    q.set("q", opts.q.trim());
  }
  return jsonFetch(`${base}/debug/canonical/actors?${q}`);
}

export async function fetchRelationshipsPage(
  base: string,
  opts: { limit: number; offset: number; currentOnly?: boolean },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
    current_only: String(opts.currentOnly ?? true),
  });
  return jsonFetch(`${base}/debug/canonical/relationships?${q}`);
}

export async function fetchExternalReferencesPage(
  base: string,
  opts: { limit: number; offset: number },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
  });
  return jsonFetch(`${base}/debug/canonical/external-references?${q}`);
}

export type RelEndpoint = { type: string; id: string; label: string };

export type ArtifactDetailResponse = {
  artifact: {
    id: string;
    artifact_kind: string;
    artifact_kind_id: number;
    title: string | null;
    summary: string | null;
    status: string | null;
    created_at: string;
    last_observed_at: string | null;
  };
  relationships: {
    id: string;
    relation_kind: string;
    subject: RelEndpoint;
    object: RelEndpoint;
    valid_from: string;
    valid_to: string | null;
  }[];
  external_references: {
    id: string;
    external_key: string;
    connector: string;
    last_raw_record_id: number | null;
  }[];
};

export async function fetchArtifactDetail(
  base: string,
  artifactId: string,
): Promise<ArtifactDetailResponse> {
  return jsonFetch(`${base}/debug/canonical/artifacts/${encodeURIComponent(artifactId)}`);
}

export type ActorDetailResponse = {
  actor: {
    id: string;
    kind: string;
    display_name: string | null;
    created_at: string;
  };
  external_identities: {
    id: string;
    connector: string;
    external_id: string;
    last_observed_at: string | null;
  }[];
  relationships: ArtifactDetailResponse["relationships"];
};

export async function fetchActorDetail(base: string, actorId: string): Promise<ActorDetailResponse> {
  return jsonFetch(`${base}/debug/canonical/actors/${encodeURIComponent(actorId)}`);
}

export type MappingEventRow = {
  id: number;
  external_reference_id?: string;
  rule_version: string;
  effective_at: string;
  payload_hash?: string | null;
};

export async function fetchMappingEventsForXref(
  base: string,
  externalReferenceId: string,
): Promise<Paginated<MappingEventRow>> {
  const q = new URLSearchParams({
    limit: "50",
    offset: "0",
    external_reference_id: externalReferenceId,
  });
  return jsonFetch(`${base}/debug/canonical/mapping-events?${q}`);
}

export type CanonicalStatusResponse = {
  tenant_id: string;
  connection_id: string;
  connector: string;
  step3_last_processed_replay_sequence: number;
  step3_last_processed_id: number;
  step3_lag_rows: number;
  step3_last_processed_timestamp: string | null;
  step2_watermark_replay_sequence: number;
  step2_watermark_id: number;
};

export async function fetchCanonicalStatus(
  base: string,
  connectionId: string,
  connector = "github",
): Promise<CanonicalStatusResponse> {
  const q = new URLSearchParams({
    connection_id: connectionId,
    connector,
  });
  return jsonFetch(`${base}/debug/canonical/status?${q}`);
}

export type CanonicalResetResyncResponse = {
  reset: boolean;
  connection_id: string;
  ingestion_run_id: string;
  ingestion_status: string;
  projection_rows_processed: number;
  canonical_rows_processed: number;
  warning: string | null;
};

export async function resetAndResyncCanonical(
  base: string,
  connectionId: string,
): Promise<CanonicalResetResyncResponse> {
  const q = new URLSearchParams({
    connection_id: connectionId,
    connector: "github",
    confirm: "RESET",
  });
  const res = await fetch(`${base}/debug/canonical/reset-and-resync?${q}`, {
    method: "POST",
    credentials: "include",
  });
  if (res.status === 401) {
    throw new Error("Not signed in");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return (await res.json()) as CanonicalResetResyncResponse;
}

export type RebuildFromStep1Response = {
  rebuilt_from_step1: boolean;
  connection_id: string;
  projection_rows_processed: number;
  canonical_rows_processed: number;
};

export async function rebuildFromStep1Canonical(
  base: string,
  connectionId: string,
): Promise<RebuildFromStep1Response> {
  const q = new URLSearchParams({
    connection_id: connectionId,
    connector: "github",
    confirm: "REBUILD",
  });
  const res = await fetch(`${base}/debug/canonical/rebuild-from-step1?${q}`, {
    method: "POST",
    credentials: "include",
  });
  if (res.status === 401) {
    throw new Error("Not signed in");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return (await res.json()) as RebuildFromStep1Response;
}

export type SubgraphResponse = {
  anchor: { type: "artifact" | "actor"; id: string };
  depth: number;
  nodes: {
    id: string;
    node_type: "artifact" | "actor";
    artifact_kind: string | null;
    actor_kind: string | null;
    label: string | null;
    status: string | null;
    last_observed_at: string | null;
  }[];
  edges: {
    id: string;
    source_id: string;
    target_id: string;
    relation_kind: string;
    directed: boolean;
    valid_from: string;
    valid_to: string | null;
  }[];
  truncated: boolean;
  truncation_reason: string | null;
};

export async function fetchSubgraphByArtifact(
  base: string,
  artifactId: string,
  depth: number,
): Promise<SubgraphResponse> {
  const q = new URLSearchParams({
    artifact_id: artifactId,
    depth: String(Math.min(depth, 2)),
  });
  return jsonFetch(`${base}/debug/canonical/subgraph?${q}`);
}

export async function fetchSubgraphByActor(
  base: string,
  actorId: string,
  depth: number,
): Promise<SubgraphResponse> {
  const q = new URLSearchParams({
    actor_id: actorId,
    depth: String(Math.min(depth, 2)),
  });
  return jsonFetch(`${base}/debug/canonical/subgraph?${q}`);
}

export type IngestionRunsResponse = {
  items: { id: string; connection_id: string }[];
};

export async function fetchGithubIngestionRuns(base: string): Promise<IngestionRunsResponse> {
  return jsonFetch(`${base}/connectors/github/ingestion/runs`);
}
