/** Fetch helpers for Step 3 canonical debug (session cookie or admin Basic). */

export function getApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL;
  if (typeof raw !== "string" || !raw.trim()) {
    return "http://localhost:8000";
  }
  return raw.replace(/\/$/, "");
}

/** Client for `/debug/canonical` (product session) or `/admin/tenants/:id/canonical` (Basic). */
export type CanonicalClient =
  | { kind: "session"; base: string }
  | { kind: "admin"; base: string; tenantId: string; password: string; basicUser?: string };

export function sessionCanonicalClient(): CanonicalClient {
  return { kind: "session", base: getApiBase() };
}

export function adminCanonicalClient(tenantId: string, password: string): CanonicalClient {
  return { kind: "admin", base: getApiBase(), tenantId, password };
}

function canonicalPrefix(c: CanonicalClient): string {
  if (c.kind === "session") {
    return `${c.base}/debug/canonical`;
  }
  return `${c.base}/admin/tenants/${c.tenantId}/canonical`;
}

function fetchInit(c: CanonicalClient, init?: RequestInit): RequestInit {
  if (c.kind === "session") {
    return { ...init, credentials: "include" };
  }
  const u = c.basicUser ?? "admin";
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Basic ${btoa(`${u}:${c.password}`)}`);
  return { ...init, headers };
}

/** One entry from FastAPI / Pydantic validation errors (422). */
type FastApiValidationItem = {
  loc?: unknown[];
  msg?: string;
  type?: string;
};

function lastLocField(loc: unknown[] | undefined): string {
  if (!loc?.length) {
    return "field";
  }
  const last = loc[loc.length - 1];
  return typeof last === "string" ? last : "field";
}

function fieldHeading(key: string): string {
  switch (key) {
    case "email":
      return "Email";
    case "password":
      return "Password";
    case "full_name":
      return "Full name";
    case "company_name":
      return "Company";
    default:
      return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

/** Turn validation items into short, user-facing sentences. */
function formatValidationErrors(items: FastApiValidationItem[]): string {
  const parts: string[] = [];
  for (const item of items) {
    const key = lastLocField(item.loc);
    const t = item.type ?? "";
    const m = (item.msg ?? "").toLowerCase();

    if (key === "email" && (t.includes("email") || m.includes("email") || m.includes("@"))) {
      parts.push("Use a valid email with a domain (e.g. you@company.com).");
      continue;
    }
    if (key === "password") {
      if (t === "string_too_short" || m.includes("at least")) {
        parts.push("Password must be at least 8 characters.");
        continue;
      }
      if (t === "string_too_long" || m.includes("at most")) {
        parts.push("Password is too long.");
        continue;
      }
    }
    if ((key === "full_name" || key === "company_name") && (t === "string_too_long" || m.includes("at most"))) {
      parts.push(`${fieldHeading(key)} is too long.`);
      continue;
    }

    const raw = item.msg?.trim();
    if (raw) {
      const short = raw.replace(/^value error,\s*/i, "").replace(/^string\s+/i, "");
      parts.push(`${fieldHeading(key)}: ${short}`);
    }
  }

  const unique = [...new Set(parts)];
  return unique.length > 0
    ? unique.join(" ")
    : "Please check your input and try again.";
}

export async function readErrorDetail(res: Response): Promise<string> {
  const fallback = `Something went wrong (HTTP ${res.status}). Try again.`;
  try {
    const data = (await res.json()) as { detail?: string | FastApiValidationItem[] | Record<string, unknown> };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (first && typeof first === "object" && ("loc" in first || "msg" in first)) {
        return formatValidationErrors(data.detail as FastApiValidationItem[]);
      }
    }
  } catch {
    /* ignore */
  }
  return res.status === 422 ? formatValidationErrors([]) : fallback;
}

async function canonJson<T>(c: CanonicalClient, pathAndQuery: string): Promise<T> {
  const url = `${canonicalPrefix(c)}/${pathAndQuery}`;
  const res = await fetch(url, fetchInit(c));
  if (res.status === 401) {
    throw new Error(c.kind === "session" ? "Not signed in" : "Admin authentication failed");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<T>;
}

type Paginated<T> = {
  total: number;
  limit: number;
  offset: number;
  items: T[];
};

/** Seeded registry ids — see migration `20260324_0011_step3_canonical_ontology`. */
const RELATION_KIND_BY_ID: Record<number, string> = {
  1: "authored_by",
  2: "associated_with",
  3: "contains",
};

export function relationKindName(id: number | null | undefined): string {
  if (id == null) {
    return "—";
  }
  return RELATION_KIND_BY_ID[id] ?? String(id);
}

export async function fetchArtifactsPage(
  c: CanonicalClient,
  opts: { limit: number; offset: number; q?: string },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
  });
  if (opts.q?.trim()) {
    q.set("q", opts.q.trim());
  }
  return canonJson(c, `artifacts?${q}`);
}

export async function fetchActorsPage(
  c: CanonicalClient,
  opts: { limit: number; offset: number; q?: string },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
  });
  if (opts.q?.trim()) {
    q.set("q", opts.q.trim());
  }
  return canonJson(c, `actors?${q}`);
}

export async function fetchRelationshipsPage(
  c: CanonicalClient,
  opts: { limit: number; offset: number; currentOnly?: boolean },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
    current_only: String(opts.currentOnly ?? true),
  });
  return canonJson(c, `relationships?${q}`);
}

export async function fetchExternalReferencesPage(
  c: CanonicalClient,
  opts: { limit: number; offset: number },
): Promise<Paginated<Record<string, unknown>>> {
  const q = new URLSearchParams({
    limit: String(opts.limit),
    offset: String(opts.offset),
  });
  return canonJson(c, `external-references?${q}`);
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
  c: CanonicalClient,
  artifactId: string,
): Promise<ArtifactDetailResponse> {
  return canonJson(c, `artifacts/${encodeURIComponent(artifactId)}`);
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

export async function fetchActorDetail(
  c: CanonicalClient,
  actorId: string,
): Promise<ActorDetailResponse> {
  return canonJson(c, `actors/${encodeURIComponent(actorId)}`);
}

type MappingEventRow = {
  id: number;
  external_reference_id?: string;
  rule_version: string;
  effective_at: string;
  payload_hash?: string | null;
};

export async function fetchMappingEventsForXref(
  c: CanonicalClient,
  externalReferenceId: string,
): Promise<Paginated<MappingEventRow>> {
  const q = new URLSearchParams({
    limit: "50",
    offset: "0",
    external_reference_id: externalReferenceId,
  });
  return canonJson(c, `mapping-events?${q}`);
}

type CanonicalStatusResponse = {
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
  c: CanonicalClient,
  connectionId: string,
  connector = "github",
): Promise<CanonicalStatusResponse> {
  const q = new URLSearchParams({
    connection_id: connectionId,
    connector,
  });
  return canonJson(c, `status?${q}`);
}

type CanonicalResetResyncResponse = {
  reset: boolean;
  connection_id: string;
  ingestion_run_id: string;
  ingestion_status: string;
  projection_rows_processed: number;
  canonical_rows_processed: number;
  warning: string | null;
};

export async function resetAndResyncCanonical(
  c: CanonicalClient,
  connectionId: string,
): Promise<CanonicalResetResyncResponse> {
  const q = new URLSearchParams({
    connection_id: connectionId,
    connector: "github",
    confirm: "RESET",
  });
  const res = await fetch(`${canonicalPrefix(c)}/reset-and-resync?${q}`, fetchInit(c, { method: "POST" }));
  if (res.status === 401) {
    throw new Error(c.kind === "session" ? "Not signed in" : "Admin authentication failed");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return (await res.json()) as CanonicalResetResyncResponse;
}

type RebuildFromStep1Response = {
  rebuilt_from_step1: boolean;
  connection_id: string;
  projection_rows_processed: number;
  canonical_rows_processed: number;
};

export async function rebuildFromStep1Canonical(
  c: CanonicalClient,
  connectionId: string,
): Promise<RebuildFromStep1Response> {
  const q = new URLSearchParams({
    connection_id: connectionId,
    connector: "github",
    confirm: "REBUILD",
  });
  const res = await fetch(
    `${canonicalPrefix(c)}/rebuild-from-step1?${q}`,
    fetchInit(c, { method: "POST" }),
  );
  if (res.status === 401) {
    throw new Error(c.kind === "session" ? "Not signed in" : "Admin authentication failed");
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
  c: CanonicalClient,
  artifactId: string,
  depth: number,
): Promise<SubgraphResponse> {
  const q = new URLSearchParams({
    artifact_id: artifactId,
    depth: String(Math.min(depth, 2)),
  });
  return canonJson(c, `subgraph?${q}`);
}

export async function fetchSubgraphByActor(
  c: CanonicalClient,
  actorId: string,
  depth: number,
): Promise<SubgraphResponse> {
  const q = new URLSearchParams({
    actor_id: actorId,
    depth: String(Math.min(depth, 2)),
  });
  return canonJson(c, `subgraph?${q}`);
}

type IngestionRunsResponse = {
  items: { id: string; connection_id: string }[];
};

export async function fetchGithubIngestionRuns(c: CanonicalClient): Promise<IngestionRunsResponse> {
  if (c.kind === "session") {
    const res = await fetch(`${c.base}/connectors/github/ingestion/runs`, fetchInit(c));
    if (res.status === 401) {
      throw new Error("Not signed in");
    }
    if (!res.ok) {
      throw new Error(await readErrorDetail(res));
    }
    const body = (await res.json()) as { items: { id: string; connection_id: string }[] };
    return { items: body.items };
  }
  const res = await fetch(
    `${c.base}/admin/tenants/${c.tenantId}/github/ingestion/runs`,
    fetchInit(c),
  );
  if (res.status === 401) {
    throw new Error("Admin authentication failed");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  const body = (await res.json()) as { items: { id: string; connection_id: string }[] };
  return { items: body.items };
}

/** Same shape as GitHub — distinct connection_ids from recent Linear Step 1 runs. */
export async function fetchLinearIngestionRuns(c: CanonicalClient): Promise<IngestionRunsResponse> {
  if (c.kind === "session") {
    const res = await fetch(`${c.base}/connectors/linear/ingestion/runs`, fetchInit(c));
    if (res.status === 401) {
      throw new Error("Not signed in");
    }
    if (!res.ok) {
      throw new Error(await readErrorDetail(res));
    }
    const body = (await res.json()) as { items: { id: string; connection_id: string }[] };
    return { items: body.items };
  }
  const res = await fetch(
    `${c.base}/admin/tenants/${c.tenantId}/linear/ingestion/runs`,
    fetchInit(c),
  );
  if (res.status === 401) {
    throw new Error("Admin authentication failed");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  const body = (await res.json()) as { items: { id: string; connection_id: string }[] };
  return { items: body.items };
}
