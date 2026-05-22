/** Shared types for GET …/cortex/canonical/coverage-matrix (substrate coverage + health aggregates). */

export type CoverageRow = {
  connector: string;
  resource_type: string;
  emitted?: boolean;
  ingest_supported: boolean;
  exhaust_row_status: string;
  routable: boolean;
  materializable: boolean;
  logical_keys: boolean;
  provenance: boolean;
  replay: boolean;
  oracle_coverage: string;
  verification_coverage: string;
  ambiguity_support: string;
  maturity_level: string;
  active?: boolean;
  dormant?: boolean;
  dead_route?: boolean;
  never_ingested?: boolean;
  never_materialized?: boolean;
  never_replayed?: boolean;
  historically_active?: boolean;
  stale?: boolean;
  inactive_by_design?: boolean;
  connector_disabled?: boolean;
  awaiting_ingestion_support?: boolean;
  replay_active?: boolean;
  topology_active?: boolean;
  replay_converged?: boolean;
  topology_safe?: boolean;
  deterministic?: boolean;
  replay_count?: number;
  replay_failure_count?: number;
  orphan_count?: number;
  topology_edge_count?: number;
  transform_routing_rule_base: string | null;
  canonical_object_kind: string | null;
  oracle_fixture_id: string | null;
  tenant_raw_row_count: number;
  tenant_materialized_row_count: number;
  tenant_materialization_pct_of_raw: number | null;
  notes: string | null;
  first_seen_at?: string | null;
  last_materialized_at?: string | null;
};

export type CoveragePayload = {
  canonical_coverage_matrix_schema_version: number;
  transform_routing_registry_version: number;
  tenant_id: string;
  summary: {
    matrix_row_count: number;
    routable_pair_count: number;
    ingest_only_pair_count: number;
    transform_only_or_unlisted_exhaust_count: number;
    unsupported_ingest_raw_row_count: number;
    routable_unmaterialized_raw_row_count: number;
    dead_route_pair_count?: number;
    dormant_route_pair_count?: number;
    replay_active_pair_count?: number;
    topology_active_pair_count?: number;
    determinism_drift_events?: number;
    orphan_backlog_pressure?: number;
    never_ingested_pair_count?: number;
    never_materialized_pair_count?: number;
    never_replayed_pair_count?: number;
    historically_active_pair_count?: number;
    stale_pair_count?: number;
    inactive_by_design_pair_count?: number;
    connector_disabled_pair_count?: number;
    awaiting_ingestion_support_pair_count?: number;
  };
  rows: CoverageRow[];
  connector_rollups?: ConnectorRollup[];
  phase03_exit_audit?: Array<Record<string, unknown>>;
};

const CORE_CONNECTORS = ["github", "slack", "linear", "notion", "calls"] as const;

export function sumCoverageTotals(rows: CoverageRow[]) {
  let raw = 0;
  let mat = 0;
  for (const r of rows) {
    raw += Number(r.tenant_raw_row_count) || 0;
    mat += Number(r.tenant_materialized_row_count) || 0;
  }
  return { raw, mat };
}

export type ConnectorRollup = {
  connector: string;
  rawRows: number;
  canonicalRows: number;
  untreatedRoutable: number;
  replayFailures: number;
  orphanRefs: number;
  coveragePct: number | null;
  lastFirstSeen: string | null;
  lastMaterialized: string | null;
  hasDeadRoute: boolean;
  hasDormant: boolean;
};

function isoMax(a: string | null, b: string | null): string | null {
  if (!b) return a;
  if (!a) return b;
  return b > a ? b : a;
}

/** Per-connector rollups for operator health table. */
export function rollupConnectors(rows: CoverageRow[]): ConnectorRollup[] {
  const m = new Map<string, ConnectorRollup>();
  function ensure(conn: string): ConnectorRollup {
    let agg = m.get(conn);
    if (!agg) {
      agg = {
        connector: conn,
        rawRows: 0,
        canonicalRows: 0,
        untreatedRoutable: 0,
        replayFailures: 0,
        orphanRefs: 0,
        coveragePct: null,
        lastFirstSeen: null,
        lastMaterialized: null,
        hasDeadRoute: false,
        hasDormant: false,
      };
      m.set(conn, agg);
    }
    return agg;
  }
  for (const c of CORE_CONNECTORS) ensure(c);
  for (const r of rows) {
    const agg = ensure(r.connector);
    const rawN = Number(r.tenant_raw_row_count) || 0;
    const matN = Number(r.tenant_materialized_row_count) || 0;
    agg.rawRows += rawN;
    agg.canonicalRows += matN;
    if (r.routable) {
      agg.untreatedRoutable += Math.max(0, rawN - matN);
    }
    agg.replayFailures += Number(r.replay_failure_count) || 0;
    agg.orphanRefs += Number(r.orphan_count) || 0;
    if (r.dead_route) agg.hasDeadRoute = true;
    if (r.dormant) agg.hasDormant = true;
    agg.lastFirstSeen = isoMax(agg.lastFirstSeen, r.first_seen_at ?? null);
    agg.lastMaterialized = isoMax(agg.lastMaterialized, r.last_materialized_at ?? null);
  }
  for (const agg of m.values()) {
    if (agg.rawRows > 0) {
      agg.coveragePct = Math.round((100 * agg.canonicalRows) / agg.rawRows);
    }
  }
  const core = new Set<string>(CORE_CONNECTORS);
  const rest = [...m.keys()].filter((k) => !core.has(k)).sort();
  return [...CORE_CONNECTORS, ...rest].map((k) => m.get(k)!);
}

/** Primary human-readable reason raw rows are not fully canonicalized for this pair. */
export function untreatedReason(r: CoverageRow): string {
  if (r.connector_disabled) return "Connector disabled";
  if (r.dead_route) return "Dead transform route (registry)";
  if (!r.ingest_supported && (r.tenant_raw_row_count ?? 0) > 0) return "Unexpected raw without ingest contract";
  if (r.ingest_supported && !r.routable && (r.tenant_raw_row_count ?? 0) > 0) return "No transform route (unsupported for canonical)";
  if (r.awaiting_ingestion_support) return "Awaiting ingestion support";
  if (r.dormant) return "Dormant route";
  if (!r.routable) return "Ingest-only (not routable)";
  const rawN = Number(r.tenant_raw_row_count) || 0;
  const matN = Number(r.tenant_materialized_row_count) || 0;
  if (rawN === 0) return "No raw rows";
  if (matN >= rawN) {
    if ((r.replay_failure_count ?? 0) > 0) return "Replay failures on materialized rows";
    if ((r.orphan_count ?? 0) > 0) return "Replay topology orphan pressure";
    return "Fully materialized";
  }
  if ((r.replay_failure_count ?? 0) > 0) return "Transform or replay failure";
  if ((r.orphan_count ?? 0) > 0) return "Missing replay parent (orphan topology)";
  return "Backlog / not yet materialized";
}

export function untreatedResourceRows(rows: CoverageRow[]): CoverageRow[] {
  return rows.filter((r) => {
    if (!r.routable) {
      return (r.tenant_raw_row_count ?? 0) > 0 && r.ingest_supported;
    }
    const rawN = Number(r.tenant_raw_row_count) || 0;
    const matN = Number(r.tenant_materialized_row_count) || 0;
    return rawN > matN || (r.replay_failure_count ?? 0) > 0 || (r.orphan_count ?? 0) > 0;
  });
}
