import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { normalizeRetrievalLegalityClassNames } from "./retrievalAdminSurfaces";
import { StatusBadge } from "./ui/StatusBadge";

type Coverage = {
  indexed_count: number;
  replay_safe_count: number;
  eligible_artifact_count: number;
  coverage_percent: number;
  replay_safe_query_percent: number;
  walk_record_count: number;
  retrieval_never_indexed: boolean;
  substrate_state: string;
  replay_posture: string;
  intentionally_excluded_count?: number;
  omission_classes?: Record<string, number>;
};

type Legality = {
  retrieval_policy_digest: string;
  legality_classes: unknown;
};

type HealthStrip = {
  substrate_state?: string;
  replay_posture?: string;
  index_epoch?: string | null;
  degraded_percent?: number;
  retrieval_completeness_percent?: number;
  last_replay_divergence_at?: string | null;
  active_alerts?: { alert_id: string; severity: string; message: string }[];
  r_leg_all_passed?: boolean;
};

type Overview = {
  health_strip?: HealthStrip;
};

type BootstrapResult = {
  index_epoch: string;
  entry_count: number;
  entries_materialized: number;
  tcre_jobs_processed: number;
  walks_materialized: number;
  graph_links_materialized: number;
  build_state: string;
};

function invalidateRetrievalQueries(qc: ReturnType<typeof useQueryClient>, tenantId: string) {
  void qc.invalidateQueries({ queryKey: ["retrieval-overview", tenantId] });
  void qc.invalidateQueries({ queryKey: ["retrieval-coverage", tenantId] });
  void qc.invalidateQueries({ queryKey: ["retrieval-legality", tenantId] });
  void qc.invalidateQueries({ queryKey: ["retrieval-index", tenantId] });
  void qc.invalidateQueries({ queryKey: ["admin-substrate-completeness", tenantId] });
}

export default function AdminCortexRetrievalOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const overview = useQuery({
    queryKey: ["retrieval-overview", tenantId],
    queryFn: () => adminJson<Overview>(`/admin/tenants/${tenantId}/cortex/retrieval/overview`),
  });
  const coverage = useQuery({
    queryKey: ["retrieval-coverage", tenantId],
    queryFn: () => adminJson<Coverage>(`/admin/tenants/${tenantId}/cortex/retrieval/coverage`),
  });
  const legality = useQuery({
    queryKey: ["retrieval-legality", tenantId],
    queryFn: () => adminJson<Legality>(`/admin/tenants/${tenantId}/cortex/retrieval/legality`),
  });

  const bootstrapMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/retrieval/index/bootstrap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json() as Promise<BootstrapResult>;
    },
    onSuccess: () => invalidateRetrievalQueries(qc, tenantId),
  });

  const c = coverage.data;
  const l = legality.data;
  const legalityClassNames = normalizeRetrievalLegalityClassNames(l?.legality_classes);
  const health = overview.data?.health_strip;
  const showBootstrapCta =
    c &&
    (c.retrieval_never_indexed ||
      c.indexed_count === 0 ||
      (c.eligible_artifact_count > 0 && c.coverage_percent < 5));

  return (
    <div className="space-y-4">
      {health && (
        <section className="rounded-lg border border-stone-200 bg-stone-50 p-3 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
              Runtime health
            </span>
            <StatusBadge tone={health.substrate_state === "healthy" ? "ok" : "warn"}>
              {health.substrate_state ?? "unknown"}
            </StatusBadge>
            <StatusBadge tone={health.replay_posture === "stable" ? "ok" : "warn"}>
              replay: {health.replay_posture ?? "unknown"}
            </StatusBadge>
            {health.r_leg_all_passed === false && (
              <StatusBadge tone="warn">R-LEG violations</StatusBadge>
            )}
            <span className="text-xs text-stone-600">
              completeness {health.retrieval_completeness_percent ?? 0}% · degraded queries{" "}
              {health.degraded_percent ?? 0}%
              {health.index_epoch ? ` · epoch ${health.index_epoch}` : ""}
            </span>
          </div>
          {(health.active_alerts?.length ?? 0) > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-amber-900">
              {health.active_alerts?.map((a) => (
                <li key={a.alert_id}>
                  [{a.severity}] {a.message}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {showBootstrapCta && (
        <section className="rounded-lg border border-violet-200 bg-violet-50 p-4 shadow-sm">
          <h3 className="font-semibold text-violet-950">Index not materialized</h3>
          <p className="mt-1 text-sm text-violet-900">
            Retrieval coverage is empty because no index epoch has been built from upstream TCRE jobs,
            completed walks, and org links. Use bootstrap to materialize entries and publish a new epoch
            (safe operator action — no confirmation phrase).
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="rounded-lg bg-violet-800 px-3 py-2 text-sm font-medium text-white hover:bg-violet-900 disabled:opacity-50"
              disabled={bootstrapMut.isPending}
              onClick={() => bootstrapMut.mutate()}
            >
              {bootstrapMut.isPending ? "Bootstrapping index…" : "Bootstrap retrieval index"}
            </button>
            <Link
              to={`/admin/tenants/${tenantId}/cortex/retrieval/index`}
              className="rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm font-medium text-violet-900 hover:bg-violet-100"
            >
              Advanced index controls
            </Link>
          </div>
          {bootstrapMut.error && (
            <p className="mt-2 text-sm text-red-700">{(bootstrapMut.error as Error).message}</p>
          )}
          {bootstrapMut.data && (
            <p className="mt-2 text-xs text-violet-900">
              Published epoch <span className="font-mono">{bootstrapMut.data.index_epoch}</span> with{" "}
              {bootstrapMut.data.entry_count} entries (
              {bootstrapMut.data.entries_materialized} materialized from{" "}
              {bootstrapMut.data.tcre_jobs_processed} TCRE jobs, {bootstrapMut.data.walks_materialized}{" "}
              walks, {bootstrapMut.data.graph_links_materialized} org links).
            </p>
          )}
        </section>
      )}

      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-stone-900">Retrieval substrate coverage</h2>
          {c && (
            <StatusBadge tone={c.substrate_state === "healthy" ? "ok" : "warn"}>
              {c.substrate_state}
            </StatusBadge>
          )}
        </div>
        {coverage.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {c && (
          <>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-stone-500">Eligible artifacts</dt>
                <dd className="text-2xl font-semibold">{c.eligible_artifact_count}</dd>
              </div>
              <div>
                <dt className="text-stone-500">Indexed (published epoch)</dt>
                <dd className="text-2xl font-semibold">{c.indexed_count}</dd>
              </div>
              <div>
                <dt className="text-stone-500">Replay-safe index rows</dt>
                <dd className="text-2xl font-semibold text-emerald-800">{c.replay_safe_count}</dd>
              </div>
              <div>
                <dt className="text-stone-500">Coverage</dt>
                <dd className="text-2xl font-semibold">{c.coverage_percent}%</dd>
              </div>
            </dl>
            <p className="mt-2 text-xs text-stone-500">
              Walk records: {c.walk_record_count} · Replay posture: {c.replay_posture}
              {c.retrieval_never_indexed ? " · Index never built" : ""}
              {(c.intentionally_excluded_count ?? 0) > 0
                ? ` · Pending index builds: ${c.intentionally_excluded_count}`
                : ""}
            </p>
          </>
        )}
      </section>
      {l && (
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h3 className="font-semibold text-stone-900">Retrieval policy</h3>
          <p className="mt-1 font-mono text-xs text-stone-600">{l.retrieval_policy_digest}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {legalityClassNames.map((cls) => (
              <StatusBadge key={cls} tone={cls.includes("safe") ? "ok" : "warn"}>
                {cls}
              </StatusBadge>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
