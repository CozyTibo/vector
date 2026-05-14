import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import type {
  CortexCanonicalControlPlane,
  CortexOverview,
  CortexRawStats,
} from "./cortexAdminTypes";
import { formatRelativeAge } from "./cortexAdminTypes";
import type { GraphForensicView, SnapshotCardTier } from "./graph/graphControlPlaneTypes";
import { GRAPH_FORENSIC_VIEWS, getGraphControlPlaneMock } from "./graph/graphControlPlaneMock";
import { StatusBadge } from "./ui/StatusBadge";

/** Hours — last raw fetch or completed sync run newer than this reads as “current ingestion”. */
const INGESTION_FRESH_OK_HOURS = 72;
/** Beyond this age, ingestion is explicitly “stale” for the badge (still shows relative time). */
const INGESTION_STALE_WARN_HOURS = 168;

function parseIsoMs(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return Number.isFinite(t) ? t : null;
}

function latestIngestionActivityMs(overview: CortexOverview | undefined, raw: CortexRawStats | undefined): number | null {
  let max: number | null = null;
  for (const r of raw?.connector_rollups ?? []) {
    const m = parseIsoMs(r.newest_fetched_at);
    if (m != null) max = max == null ? m : Math.max(max, m);
  }
  for (const c of overview?.connectors ?? []) {
    const lr = c.latest_run;
    if (!lr?.finished_at) continue;
    const st = (lr.status ?? "").toUpperCase();
    if (st === "COMPLETED" || st === "SUCCESS") {
      const m = parseIsoMs(lr.finished_at);
      if (m != null) max = max == null ? m : Math.max(max, m);
    }
  }
  return max;
}

function routedIngestionFailed(overview: CortexOverview | undefined): boolean {
  return Boolean(overview?.connectors.some((c) => c.cortex_routed && c.latest_run?.status === "FAILED"));
}

type LiveBadgeTone = "ok" | "warn" | "bad" | "neutral";

function ingestionFreshnessBadge(args: {
  overview: CortexOverview | undefined;
  raw: CortexRawStats | undefined;
  loading: boolean;
  error: boolean;
}): { tone: LiveBadgeTone; title: string; body: string } {
  if (args.loading && !args.overview && !args.raw) {
    return { tone: "neutral", title: "Checking ingestion…", body: "Loading raw + connector overview." };
  }
  if (args.error) {
    return {
      tone: "warn",
      title: "Ingestion signal unavailable",
      body: "Could not load ingestion endpoints — refresh or open Ingestion for detail.",
    };
  }
  const failed = routedIngestionFailed(args.overview);
  const latestMs = latestIngestionActivityMs(args.overview, args.raw);
  if (latestMs == null) {
    return {
      tone: failed ? "bad" : "warn",
      title: failed ? "Ingestion not healthy" : "No recent ingestion timestamps",
      body: failed
        ? "At least one routed connector shows a FAILED sync run."
        : "No newest_fetched_at on raw rollups and no completed sync runs — tenant may be idle or not yet ingesting.",
    };
  }
  const ageHours = (Date.now() - latestMs) / 3_600_000;
  const rel = formatRelativeAge(new Date(latestMs).toISOString());
  if (failed) {
    return {
      tone: "bad",
      title: "Ingestion degraded",
      body: `Latest successful activity ${rel}, but a routed connector shows FAILED — reconcile on Ingestion.`,
    };
  }
  if (ageHours <= INGESTION_FRESH_OK_HOURS) {
    return {
      tone: "ok",
      title: "Up to date with latest ingested data",
      body: `Latest raw fetch or completed sync activity ${rel} — within ${INGESTION_FRESH_OK_HOURS}h window.`,
    };
  }
  if (ageHours <= INGESTION_STALE_WARN_HOURS) {
    return {
      tone: "warn",
      title: "Ingestion aging",
      body: `Last activity ${rel} — older than ${INGESTION_FRESH_OK_HOURS}h but inside ${INGESTION_STALE_WARN_HOURS}h watch window.`,
    };
  }
  return {
    tone: "bad",
    title: "Ingestion stale vs expectation",
    body: `Last activity ${rel} — beyond ${INGESTION_STALE_WARN_HOURS}h; confirm schedulers and connectors.`,
  };
}

function pipelineConsistencyBadge(args: {
  overview: CortexOverview | undefined;
  cp: CortexCanonicalControlPlane | undefined;
  loading: boolean;
  error: boolean;
}): { tone: LiveBadgeTone; title: string; body: string } {
  if (args.loading && !args.cp) {
    return { tone: "neutral", title: "Checking substrate…", body: "Loading canonical control plane." };
  }
  if (args.error || !args.cp) {
    return {
      tone: "warn",
      title: "Consistency signal incomplete",
      body: "Canonical control plane did not load — open Canonical health for authoritative checks.",
    };
  }
  const h = args.cp.health_overview;
  const worker = args.overview?.worker_telemetry;
  const dup = args.overview?.duplicate_prevention;

  const badReasons: string[] = [];
  const warnReasons: string[] = [];

  if (h.active_canonical_failure_count > 0) {
    badReasons.push(`${h.active_canonical_failure_count} active canonical failure case(s)`);
  }
  if (!args.cp.verification_checklist.passed) {
    badReasons.push("canonical verification checklist not passing");
  }
  if (h.replay_dependency_cycle_detected) {
    badReasons.push("replay dependency cycle detected");
  }
  if (h.last_verification_passed === false) {
    badReasons.push("last verification run failed");
  }

  if (worker && worker.status !== "ok") {
    warnReasons.push(`workers: ${worker.status}`);
  }
  if (dup && dup.status === "warn") {
    warnReasons.push("duplicate prevention warn");
  }
  if (dup && dup.status === "unavailable") {
    warnReasons.push("duplicate prevention unavailable");
  }
  if (h.verification_freshness_label === "stale") {
    warnReasons.push("verification ledger marked stale");
  }
  if (h.ambiguity_explosion_warn) {
    warnReasons.push("ambiguity explosion warning");
  }
  if ((h.ambiguity_open_count ?? 0) > 0) {
    warnReasons.push(`${h.ambiguity_open_count} open ambiguities`);
  }
  if (routedIngestionFailed(args.overview)) {
    warnReasons.push("ingestion run FAILED on a routed connector");
  }

  if (badReasons.length > 0) {
    return {
      tone: "bad",
      title: "Substrate not in normal range",
      body: badReasons.join(" · "),
    };
  }
  if (warnReasons.length > 0) {
    return {
      tone: "warn",
      title: "Operating with attention items",
      body: warnReasons.join(" · "),
    };
  }
  return {
    tone: "ok",
    title: "Consistent / behaving normally",
    body:
      "Workers healthy, duplicate prevention clear, no active canonical failures, verification checklist passing, no replay dependency cycle — canonical control plane snapshot.",
  };
}

function overallTone(s: string): "ok" | "warn" | "bad" | "neutral" {
  if (s === "healthy") return "ok";
  if (s === "degraded" || s === "drift_detected" || s === "rebuilding") return "warn";
  if (s === "replay_divergence" || s === "unverifiable") return "bad";
  return "neutral";
}

function rowStatusTone(s: string): "ok" | "warn" | "bad" | "neutral" {
  if (s === "healthy") return "ok";
  if (s === "degraded" || s === "rebuilding") return "warn";
  if (s === "blocked") return "bad";
  return "neutral";
}

function readinessTone(d: string): "ok" | "warn" | "bad" | "neutral" {
  if (d === "pass") return "ok";
  if (d === "warn") return "warn";
  if (d === "fail") return "bad";
  return "neutral";
}

function severityTone(s: string): "ok" | "warn" | "bad" | "neutral" {
  if (s === "info") return "neutral";
  if (s === "warn") return "warn";
  if (s === "critical") return "bad";
  return "neutral";
}

function GraphStatCard(props: {
  label: string;
  value: string;
  tone: "ok" | "warn" | "bad";
  freshness: string;
  hint?: string;
  to?: string;
  subdued?: boolean;
}) {
  const strongBorder =
    props.tone === "bad"
      ? "border-red-200 bg-red-50/80"
      : props.tone === "warn"
        ? "border-amber-200 bg-amber-50/70"
        : "border-emerald-200 bg-emerald-50/50";
  const border = props.subdued ? "border-stone-200 bg-stone-50/95" : strongBorder;
  const valueCls = props.subdued ? "mt-1 text-xl font-semibold tabular-nums text-stone-800" : "mt-1 text-2xl font-semibold tabular-nums text-stone-900";
  const labelCls = props.subdued
    ? "text-[10px] font-semibold uppercase tracking-wide text-stone-500"
    : "text-[10px] font-semibold uppercase tracking-wide text-stone-600";
  const inner = (
    <div className={`rounded-xl border p-4 shadow-sm ${border}`} title={props.hint}>
      <p className={labelCls}>{props.label}</p>
      <p className={valueCls}>{props.value}</p>
      <p className="mt-2 text-[10px] font-medium uppercase tracking-wide text-stone-500">{props.freshness}</p>
    </div>
  );
  if (props.to) {
    return (
      <Link to={props.to} className="block transition hover:opacity-90">
        {inner}
      </Link>
    );
  }
  return inner;
}

function snapshotCardsByTier(
  cards: Array<{
    id: string;
    label: string;
    value: string;
    tone: "ok" | "warn" | "bad";
    freshness: string;
    hint?: string;
    linkTo?: "verification" | "memory" | "canonical_replay" | "canonical_health" | "explorer";
    tier: SnapshotCardTier;
  }>,
  tier: SnapshotCardTier,
) {
  return cards.filter((c) => c.tier === tier);
}

function cardHref(
  tenantId: string,
  link?: "verification" | "memory" | "canonical_replay" | "canonical_health" | "explorer",
): string | undefined {
  if (!link) return undefined;
  const base = `/admin/tenants/${tenantId}/cortex`;
  if (link === "verification") return `${base}/verification`;
  if (link === "memory") return `${base}/memory`;
  if (link === "canonical_replay") return `${base}/canonical/advanced/replay`;
  if (link === "canonical_health") return `${base}/canonical/health`;
  if (link === "explorer") return `${base}/graph#traversal-explorer`;
  return undefined;
}

function forensicViewLabel(v: GraphForensicView): string {
  const labels: Record<GraphForensicView, string> = {
    path: "walk path",
    edge_provenance: "edge provenance",
    causal_chain: "causal chain",
    recon_route: "reconstruction route",
    drift_origin: "drift origin",
    contradictions: "contradictions",
    replay_evidence: "replay evidence",
    anchor_lineage: "temporal anchor lineage",
    lineage: "walk provenance lineage",
    edge_table: "edge sample (tsv)",
    continuity: "continuity inspection",
    minimap: "validity sketch",
  };
  return labels[v];
}

function placeholderAction(label: string) {
  window.alert(
    `Not wired — "${label}" would enqueue a bounded, replay-safe operator action on the OCTS walk substrate (no graph hand-editing).`,
  );
}

export default function AdminCortexGraphPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const data = useMemo(() => getGraphControlPlaneMock(tenantId), [tenantId]);
  const [explorerQuery, setExplorerQuery] = useState("");
  const [explorerView, setExplorerView] = useState<GraphForensicView>("path");

  const qOverview = useQuery({
    queryKey: ["admin-cortex-overview", tenantId],
    queryFn: () => adminJson<CortexOverview>(`/admin/tenants/${tenantId}/cortex/ingestion`),
    enabled: Boolean(tenantId),
  });
  const qRaw = useQuery({
    queryKey: ["admin-cortex-raw-stats", tenantId],
    queryFn: () => adminJson<CortexRawStats>(`/admin/tenants/${tenantId}/cortex/ingestion/raw-stats`),
    enabled: Boolean(tenantId),
  });
  const qCp = useQuery({
    queryKey: ["admin-cortex-canonical-control-plane", tenantId],
    queryFn: () =>
      adminJson<CortexCanonicalControlPlane>(`/admin/tenants/${tenantId}/cortex/canonical/control-plane`),
    enabled: Boolean(tenantId),
  });

  const ingestLoading = qOverview.isPending || qRaw.isPending;
  const ingestError = qOverview.isError || qRaw.isError;
  const canonLoading = qCp.isPending;
  const canonError = qCp.isError;

  const liveIngestion = useMemo(
    () =>
      ingestionFreshnessBadge({
        overview: qOverview.data,
        raw: qRaw.data,
        loading: ingestLoading,
        error: ingestError,
      }),
    [qOverview.data, qRaw.data, ingestLoading, ingestError],
  );

  const liveConsistency = useMemo(
    () =>
      pipelineConsistencyBadge({
        overview: qOverview.data,
        cp: qCp.data,
        loading: canonLoading,
        error: canonError,
      }),
    [qOverview.data, qCp.data, canonLoading, canonError],
  );

  const primaryCards = snapshotCardsByTier(data.snapshot.cards, "primary");
  const secondaryCards = snapshotCardsByTier(data.snapshot.cards, "secondary");
  const operationalCards = snapshotCardsByTier(data.snapshot.cards, "operational");

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-700">Cortex · Graph</p>
            <h1 className="mt-1 text-xl font-semibold text-stone-900">Organizational Graph Control Plane</h1>
            <p className="mt-2 max-w-3xl text-sm text-stone-600">
              Constitutional control plane for{" "}
              <span className="font-medium text-stone-800">bounded, replay-safe organizational walks</span> (Phase 05
              OCTS): walk legality, deterministic ordering, continuity-safe projections, and replay-generated traversal
              artifacts — not a semantic knowledge graph or graph-database console.
            </p>
            <p className="mt-2 text-xs text-stone-500">
              Walk substrate snapshot as of {data.snapshot.updatedAt} (mock payload until API routes land).
            </p>
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-950">
              <p className="font-semibold text-amber-950">Operator notice — this tab is not wired to live substrate</p>
              <p className="mt-1 leading-relaxed text-amber-900/95">
                Every card, table, and forensic line here is a <span className="font-medium">deterministic demo</span>{" "}
                derived only from the tenant id in the URL. It does <span className="font-medium">not</span> read raw
                memory, canonical rows, identity org links, Celery{" "}
                <span className="font-mono">flush_rerun_to_identity</span> (through Phase 05 projection), or admin OCTS
                walk APIs — so <span className="font-medium">Flush + rerun through Phase 05 will not change these numbers</span>.
                To verify a real rerun: check{" "}
                <Link className="font-medium text-amber-950 underline" to={`/admin/tenants/${tenantId}/cortex/canonical/health`}>
                  Canonical health
                </Link>
                ,{" "}
                <Link className="font-medium text-amber-950 underline" to={`/admin/tenants/${tenantId}/cortex/ingestion`}>
                  Ingestion / replay jobs
                </Link>
                , and org-link replay jobs for <span className="font-mono">graph_projection_export</span> (Phase 05
                ingress receipt).
              </p>
            </div>
            <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/50 p-3 text-xs text-emerald-950">
              <p className="font-semibold text-emerald-950">Live tenant signals (API-backed, not the demo walk)</p>
              <p className="mt-1 leading-relaxed text-emerald-900/95">
                These two badges read the same ingestion and canonical control-plane JSON as the rest of Cortex admin.
                They describe <span className="font-medium">real pipeline state</span>, not the deterministic Graph tab
                mock above.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-emerald-200/80 bg-white/90 p-3 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge tone={liveIngestion.tone === "neutral" ? "neutral" : liveIngestion.tone}>
                      {liveIngestion.title}
                    </StatusBadge>
                    <Link
                      className="text-[11px] font-medium text-emerald-900 underline"
                      to={`/admin/tenants/${tenantId}/cortex/ingestion`}
                    >
                      Ingestion →
                    </Link>
                  </div>
                  <p className="mt-2 leading-relaxed text-stone-700">{liveIngestion.body}</p>
                </div>
                <div className="rounded-md border border-emerald-200/80 bg-white/90 p-3 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge tone={liveConsistency.tone === "neutral" ? "neutral" : liveConsistency.tone}>
                      {liveConsistency.title}
                    </StatusBadge>
                    <Link
                      className="text-[11px] font-medium text-emerald-900 underline"
                      to={`/admin/tenants/${tenantId}/cortex/canonical/health`}
                    >
                      Canonical health →
                    </Link>
                  </div>
                  <p className="mt-2 leading-relaxed text-stone-700">{liveConsistency.body}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">Walk substrate status</span>
            <StatusBadge tone={overallTone(data.snapshot.overall)}>{data.snapshot.overall.replace(/_/g, " ")}</StatusBadge>
          </div>
        </div>
        <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50/80 p-3 text-xs text-stone-700">
          <p className="font-semibold text-stone-900">Anti-cognition boundary (OCTS)</p>
          <p className="mt-1 leading-relaxed text-stone-600">
            Traversal is restricted to <span className="font-medium text-stone-800">bounded replay-safe walks</span>{" "}
            over schema-first contracts. There is <span className="font-medium text-stone-800">no semantic reasoning</span>{" "}
            layer here. Closed walk algebra, forbidden cognition classes in verification bundles, and deterministic
            receipts — operator law, not product marketing.
          </p>
        </div>
      </section>

      {/* Section 1 — walk + traversal snapshot */}
      <section id="substrate-snapshot" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Walk + traversal substrate snapshot</h2>
        <p className="mt-1 text-sm text-stone-600">
          Primary: walk legality, replay equivalence, and temporal ordering. Secondary: reconstructed edge validity,
          contradiction density, and causal-chain breakpoints — deterministic graph truth, not projection vanity counts.
        </p>

        <h3 className="mt-5 text-[11px] font-semibold uppercase tracking-wide text-stone-600">
          Primary — traversal legality &amp; replay
        </h3>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {primaryCards.map((c) => (
            <GraphStatCard
              key={c.id}
              label={c.label}
              value={c.value}
              tone={c.tone}
              freshness={c.freshness}
              hint={c.hint}
              to={cardHref(tenantId, c.linkTo)}
            />
          ))}
        </div>

        <h3 className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
          Secondary — reconstructed edge truth
        </h3>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {secondaryCards.map((c) => (
            <GraphStatCard
              key={c.id}
              label={c.label}
              value={c.value}
              tone={c.tone}
              freshness={c.freshness}
              hint={c.hint}
              to={cardHref(tenantId, c.linkTo)}
              subdued
            />
          ))}
        </div>

        <h3 className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
          Operational — walk frontier &amp; replay pressure
        </h3>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {operationalCards.map((c) => (
            <GraphStatCard
              key={c.id}
              label={c.label}
              value={c.value}
              tone={c.tone}
              freshness={c.freshness}
              hint={c.hint}
              to={cardHref(tenantId, c.linkTo)}
              subdued
            />
          ))}
        </div>

        <h3 className="mt-6 text-base font-semibold text-stone-900">Walk boundedness</h3>
        <p className="mt-1 text-sm text-stone-600">
          Policy caps, frontier utilization, and bounded-walk termination — operational visibility into the walk
          primitive.
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-3 py-2 font-semibold">metric</th>
                <th className="px-3 py-2 font-semibold">value</th>
                <th className="px-3 py-2 font-semibold">limit / ref</th>
                <th className="px-3 py-2 font-semibold">notes</th>
              </tr>
            </thead>
            <tbody>
              {data.boundedness.map((row) => (
                <tr key={row.metric} className="border-t border-stone-100">
                  <td className="px-3 py-2 font-medium text-stone-900">{row.metric}</td>
                  <td className="px-3 py-2 font-mono tabular-nums text-stone-800">{row.value}</td>
                  <td className="px-3 py-2 font-mono tabular-nums text-stone-700">{row.limit}</td>
                  <td className="px-3 py-2 text-stone-600">{row.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="mt-6 text-base font-semibold text-stone-900">Temporal legality</h3>
        <p className="mt-1 text-sm text-stone-600">
          Export monotonicity, anchor continuity, and replay chronology — foundational for walk-validity intervals.
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-3 py-2 font-semibold">check</th>
                <th className="px-3 py-2 font-semibold">state</th>
                <th className="px-3 py-2 font-semibold">detail</th>
              </tr>
            </thead>
            <tbody>
              {data.temporalLegality.map((row) => (
                <tr key={row.check} className="border-t border-stone-100">
                  <td className="px-3 py-2 font-medium text-stone-900">{row.check}</td>
                  <td className="px-3 py-2">
                    <StatusBadge tone={readinessTone(row.state)}>{row.state}</StatusBadge>
                  </td>
                  <td className="px-3 py-2 text-stone-700">{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 2 */}
      <section id="topology-health" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Substrate topology health</h2>
        <p className="mt-1 text-sm text-stone-600">
          Layered substrate health from attributed reconstructed edges: evidence-backed counts, instability,
          contradictions, continuity gaps, and weak provenance — not generic vertex totals.
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-3 py-2 font-semibold">substrate layer</th>
                <th className="px-3 py-2 font-semibold">evidence-backed edges</th>
                <th className="px-3 py-2 font-semibold">unstable edges</th>
                <th className="px-3 py-2 font-semibold">contradictions</th>
                <th className="px-3 py-2 font-semibold">continuity gaps</th>
                <th className="px-3 py-2 font-semibold">weak provenance</th>
                <th className="px-3 py-2 font-semibold">walk traversal status</th>
              </tr>
            </thead>
            <tbody>
              {data.topology.map((row) => (
                <tr key={row.area} className="border-t border-stone-100">
                  <td className="px-3 py-2 font-medium text-stone-900">{row.area}</td>
                  <td className="px-3 py-2 tabular-nums text-stone-800">{row.evidenceBackedEdges}</td>
                  <td className="px-3 py-2 tabular-nums text-stone-800">{row.unstableEdges}</td>
                  <td className="px-3 py-2 tabular-nums text-stone-800">{row.contradictionIncidents}</td>
                  <td className="px-3 py-2 tabular-nums text-stone-800">{row.continuityGaps}</td>
                  <td className="px-3 py-2 tabular-nums text-stone-800">{row.weakProvenanceEdges}</td>
                  <td className="px-3 py-2">
                    <StatusBadge tone={rowStatusTone(row.traversalStatus)}>{row.traversalStatus}</StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 3 */}
      <section id="traversal-readiness" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-stone-900">Traversal readiness</h2>
            <p className="mt-1 text-sm text-stone-600">
              Constitutional laws (what must always hold) vs runtime state (what the fleet is doing now).
            </p>
          </div>
          <Link className="text-sm font-medium text-indigo-700 hover:underline" to={`/admin/tenants/${tenantId}/cortex/verification`}>
            Open Verification tab →
          </Link>
        </div>

        <h3 className="mt-5 text-sm font-semibold text-stone-900">A) Traversal constitutional laws</h3>
        <p className="mt-1 text-xs text-stone-500">Closed walk algebra, replay equivalence obligations, export monotonicity.</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {data.readinessConstitutional.map((r) => (
            <div key={r.id} className="rounded-md border border-stone-200 bg-stone-50/50 p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] font-semibold text-stone-900">{r.label}</span>
                <StatusBadge tone={readinessTone(r.decision)}>{r.decision}</StatusBadge>
              </div>
              <p className="mt-2 text-xs text-stone-600">{r.detail}</p>
              <p className="mt-2 text-[10px] font-medium uppercase tracking-wide text-stone-500">{r.doctrineRef}</p>
            </div>
          ))}
        </div>

        <h3 className="mt-6 text-sm font-semibold text-stone-900">B) Traversal runtime state</h3>
        <p className="mt-1 text-xs text-stone-500">Queues, scans, API readiness, projection jobs — operational, not normative law.</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {data.readinessRuntime.map((r) => (
            <div key={r.id} className="rounded-md border border-stone-200 bg-white p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] font-semibold text-stone-900">{r.label}</span>
                <StatusBadge tone={readinessTone(r.decision)}>{r.decision}</StatusBadge>
              </div>
              <p className="mt-2 text-xs text-stone-600">{r.detail}</p>
              <p className="mt-2 text-[10px] font-medium uppercase tracking-wide text-stone-500">{r.doctrineRef}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Section 4 */}
      <section id="frontier-runtime" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Walk frontier + runtime</h2>
        <p className="mt-1 text-sm text-stone-600">
          Bounded walk execution lanes: queues, walk frontier size, walk latency, walk replay jobs, failures.
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-3 py-2 font-semibold">runtime lane</th>
                <th className="px-3 py-2 font-semibold">status</th>
                <th className="px-3 py-2 font-semibold">queue</th>
                <th className="px-3 py-2 font-semibold">walk frontier</th>
                <th className="px-3 py-2 font-semibold">avg walk latency</th>
                <th className="px-3 py-2 font-semibold">walk replay jobs</th>
                <th className="px-3 py-2 font-semibold">failures</th>
              </tr>
            </thead>
            <tbody>
              {data.runtime.map((row) => (
                <tr key={row.lane} className="border-t border-stone-100">
                  <td className="px-3 py-2 font-medium text-stone-900">{row.lane}</td>
                  <td className="px-3 py-2">
                    <StatusBadge tone={rowStatusTone(row.status)}>{row.status}</StatusBadge>
                  </td>
                  <td className="px-3 py-2 tabular-nums">{row.queue}</td>
                  <td className="px-3 py-2 tabular-nums">{row.frontierSize}</td>
                  <td className="px-3 py-2 tabular-nums">{row.avgLatencyMs} ms</td>
                  <td className="px-3 py-2 tabular-nums">{row.replayJobs}</td>
                  <td className="px-3 py-2 tabular-nums">{row.failures}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 5 */}
      <section id="graph-operations" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Traversal projection operations</h2>
        <p className="mt-1 text-sm text-stone-600">
          Regenerate or replay-verify derived walk substrate — projections are reconstructed from authoritative sources,
          not edited like a graph DB.
        </p>
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-stone-800">Safe actions</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.safeOps.map((op) => (
              <button
                key={op.id}
                type="button"
                title={op.description}
                className="rounded border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-left text-xs font-medium text-indigo-950 hover:bg-indigo-100"
                onClick={() => placeholderAction(op.label)}
              >
                {op.label}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50/40 p-4">
          <h3 className="text-sm font-semibold text-red-900">Dangerous actions</h3>
          <p className="mt-1 text-xs text-red-800">
            Destructive replay or purge operations on derived walk artifacts. Confirmation modal + operator phrase before
            enqueue.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.dangerousOps.map((op) => (
              <button
                key={op.id}
                type="button"
                title={op.description}
                className="rounded border border-red-300 bg-white px-3 py-1.5 text-left text-xs font-medium text-red-900 hover:bg-red-50"
                onClick={() =>
                  window.confirm(`Confirm dangerous action?\n\n${op.label}\n\n${op.description}`) &&
                  placeholderAction(op.label)
                }
              >
                {op.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Section 6 */}
      <section id="traversal-explorer" className="rounded-xl border border-dashed border-stone-300 bg-stone-50/60 p-5 shadow-inner">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-stone-900">Forensic execution-graph inspection</h2>
            <p className="mt-1 max-w-3xl text-sm text-stone-600">
              Deterministic debugger views: walk path, edge provenance, causal chains, reconstruction route, drift
              origins, contradictions, replay evidence, and temporal anchor lineage — substrate validation, not graph
              exploration.
            </p>
          </div>
          <span className="rounded border border-stone-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-stone-500">
            inspection only
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <input
            type="search"
            value={explorerQuery}
            onChange={(e) => setExplorerQuery(e.target.value)}
            placeholder="Walk id, replay job id, walk_result_hash, or continuity handle…"
            className="min-w-[240px] flex-1 rounded border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-900 shadow-sm"
          />
          <div className="flex flex-wrap gap-1">
            {GRAPH_FORENSIC_VIEWS.map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setExplorerView(v)}
                className={[
                  "rounded px-2 py-1 text-xs font-medium",
                  explorerView === v
                    ? "bg-indigo-600 text-white"
                    : "border border-stone-300 bg-white text-stone-700 hover:bg-stone-100",
                ].join(" ")}
              >
                {forensicViewLabel(v)}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2 rounded border border-stone-200 bg-white p-3 font-mono text-[11px] text-stone-800 shadow-sm">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-stone-500">
              Deterministic preview ({forensicViewLabel(explorerView)})
            </p>
            <pre className="whitespace-pre-wrap">{data.forensicByView[explorerView].join("\n")}</pre>
            {explorerQuery ? (
              <p className="mt-3 border-t border-stone-100 pt-2 text-stone-500">Inspection filter (mock): “{explorerQuery}”</p>
            ) : null}
          </div>
          <div className="rounded border border-stone-200 bg-white p-3 text-xs text-stone-700 shadow-sm">
            <p className="font-semibold text-stone-900">Inspect</p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-stone-600">
              <li>edge provenance + derivation policy</li>
              <li>execution causal chains + breakpoints</li>
              <li>reconstruction route vs walk provenance</li>
              <li>drift origin coupling (table + walks)</li>
              <li>contradiction classes on reconstructed edges</li>
              <li>replay + twin-run evidence</li>
              <li>temporal anchor lineage</li>
              <li>walk receipts + traversal hashes</li>
              <li>continuity inspection</li>
              <li>edge validity sketch (symbolic)</li>
            </ul>
            <p className="mt-3 text-[10px] text-stone-500">
              Wire to admin walk / replay-verify APIs — forensic only, not a graph browser.
            </p>
          </div>
        </div>
      </section>

      {/* Section 7 */}
      <section id="drift-corruption" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Walk legality drift + continuity inspection</h2>
        <p className="mt-1 text-sm text-stone-600">
          Constitutional legality, replay-safety, and recoverability — not generic “data quality” framing.
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-3 py-2 font-semibold">issue</th>
                <th className="px-3 py-2 font-semibold">severity</th>
                <th className="px-3 py-2 font-semibold">substrate layer</th>
                <th className="px-3 py-2 font-semibold">replay-safe</th>
                <th className="px-3 py-2 font-semibold">recoverable</th>
                <th className="px-3 py-2 font-semibold">operator action</th>
              </tr>
            </thead>
            <tbody>
              {data.drift.map((row) => (
                <tr key={`${row.issue}-${row.substrateLayer}`} className="border-t border-stone-100">
                  <td className="px-3 py-2 font-medium text-stone-900">{row.issue}</td>
                  <td className="px-3 py-2">
                    <StatusBadge tone={severityTone(row.severity)}>{row.severity}</StatusBadge>
                  </td>
                  <td className="px-3 py-2 text-stone-800">{row.substrateLayer}</td>
                  <td className="px-3 py-2 text-stone-800">{row.replaySafe}</td>
                  <td className="px-3 py-2 text-stone-800">{row.recoverable}</td>
                  <td className="px-3 py-2 text-stone-700">{row.operatorAction}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 8 */}
      <section id="traversal-proofs" className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-stone-900">Constitutional traversal proofs</h2>
            <p className="mt-1 text-sm text-stone-600">
              Legal artifacts for bounded walks — hashes, replay receipts, equivalence proof, cert pack integrity — not
              observability vanity metrics.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Link className="font-medium text-indigo-700 hover:underline" to={`/admin/tenants/${tenantId}/cortex/verification`}>
              Verification
            </Link>
            <span className="text-stone-300">|</span>
            <Link
              className="font-medium text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/identity-certification`}
            >
              Identity certification
            </Link>
            <span className="text-stone-300">|</span>
            <Link className="font-medium text-indigo-700 hover:underline" to={`/admin/tenants/${tenantId}/cortex/memory`}>
              Memory
            </Link>
          </div>
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {data.proofs.map((p) => (
            <div key={p.artifact} className="rounded-md border border-stone-200 p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-stone-900">{p.artifact}</span>
                <StatusBadge tone={readinessTone(p.status)}>{p.status}</StatusBadge>
              </div>
              <p className="mt-1 font-mono text-xs text-stone-800">{p.value}</p>
              <p className="mt-2 text-xs text-stone-600">{p.notes}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
