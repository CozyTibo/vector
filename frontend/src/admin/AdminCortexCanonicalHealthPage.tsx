import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import type { CortexCanonicalControlPlane } from "./cortexAdminTypes";
import { formatRelativeAge, titleConnector } from "./cortexAdminTypes";
import type { ConnectorRollup } from "./canonical/coverageMatrixTypes";
import { StatusBadge } from "./ui/StatusBadge.tsx";

type CoverageInspectorSlice = {
  summary?: Record<string, unknown>;
  coverage_connector_rollups?: ConnectorRollup[];
  coverage_totals?: { tenant_raw_row_count_sum?: number; tenant_materialized_row_count_sum?: number };
};

type FailuresPayload = {
  tenant_id: string;
  cases: Array<{
    gap_id: string;
    failure_class: string;
    degradation_state: string;
    scope_kind: string;
    source: string;
    detail_json?: Record<string, unknown>;
  }>;
};

function toneFromHealth(
  ok: boolean,
  warn: boolean,
): "ok" | "warn" | "bad" {
  if (!ok) return "bad";
  if (warn) return "warn";
  return "ok";
}

function StatCard(props: {
  label: string;
  value: string;
  tone: "ok" | "warn" | "bad";
  hint?: string;
  to?: string;
}) {
  const border =
    props.tone === "bad"
      ? "border-red-200 bg-red-50/80"
      : props.tone === "warn"
        ? "border-amber-200 bg-amber-50/70"
        : "border-emerald-200 bg-emerald-50/50";
  const inner = (
    <div className={`rounded-xl border p-4 shadow-sm ${border}`} title={props.hint}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-600">{props.label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-stone-900">{props.value}</p>
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

export default function AdminCortexCanonicalHealthPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const overview = `/admin/tenants/${tenantId}/cortex/overview`;

  const qCp = useQuery({
    queryKey: ["admin-cortex-canonical-control-plane", tenantId],
    queryFn: () => adminJson<CortexCanonicalControlPlane>(`/admin/tenants/${tenantId}/cortex/canonical/control-plane`),
    enabled: Boolean(tenantId),
  });

  const qFailures = useQuery({
    queryKey: ["admin-cortex-canonical-failures", tenantId],
    queryFn: () => adminJson<FailuresPayload>(`/admin/tenants/${tenantId}/cortex/canonical/failures`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (qCp.isPending) return <p className="text-sm text-stone-600">Loading substrate health…</p>;
  if (qCp.isError) return <p className="text-sm text-red-700">{(qCp.error as Error).message}</p>;

  const c = qCp.data;
  const h = c.health_overview;
  const insp = (c.inspectors?.coverage_inspector ?? {}) as CoverageInspectorSlice;
  const connectorRows: ConnectorRollup[] = Array.isArray(insp.coverage_connector_rollups)
    ? (insp.coverage_connector_rollups as ConnectorRollup[])
    : [];
  const totals = insp.coverage_totals;
  const rawRowSum =
    typeof totals?.tenant_raw_row_count_sum === "number"
      ? totals.tenant_raw_row_count_sum
      : connectorRows.reduce((a, r) => a + (Number(r.rawRows) || 0), 0);
  const summary = insp.summary ?? {};
  const routable = Number(summary.routable_unmaterialized_raw_row_count) || 0;
  const unsupported = Number(summary.unsupported_ingest_raw_row_count) || 0;
  const untreated = routable + unsupported;
  const div = h.replay_divergence_class_totals_recent_completed ?? {};
  const driftBad = (div.C3 ?? 0) + (div.C4 ?? 0) + (div.C5 ?? 0);
  const driftTotal = Object.values(div).reduce((a, b) => a + (typeof b === "number" ? b : 0), 0);
  const vt = c.verification_truth;
  const lastOk =
    vt && typeof vt === "object" && typeof (vt as { created_at?: string }).created_at === "string"
      ? formatRelativeAge((vt as { created_at: string }).created_at)
      : "—";

  const recentFailures = (qFailures.data?.cases ?? []).slice(0, 8);

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Substrate snapshot</h2>
        <p className="mt-1 text-sm text-stone-600">
          Ingestion → canonicalization health. Click a card to jump to detail where useful.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard
            label="Raw ingested rows"
            value={rawRowSum.toLocaleString()}
            tone="ok"
            hint="Sum of raw rows across coverage pairs"
          />
          <StatCard
            label="Canonical materialized"
            value={h.materialization_row_count.toLocaleString()}
            tone={toneFromHealth(true, false)}
            hint="Transform materialization rows"
          />
          <StatCard
            label="Untreated raw → canonical"
            value={untreated.toLocaleString()}
            tone={toneFromHealth(untreated === 0, untreated > 0)}
            hint="Routable gap + unsupported ingest volume"
          />
          <StatCard
            label="Failed materializations (registry)"
            value={h.active_canonical_failure_count.toLocaleString()}
            tone={toneFromHealth(h.active_canonical_failure_count === 0, h.active_canonical_failure_count > 0)}
          />
          <StatCard
            label="Divergence pressure (C3–C5)"
            value={driftBad > 0 ? `${driftBad} / ${driftTotal || 0}` : `${driftTotal || 0} classes`}
            tone={toneFromHealth(driftBad === 0, driftBad > 0)}
            hint="Historical divergence tallies (read-only)"
          />
          <StatCard
            label="Last verification run"
            value={lastOk}
            tone={toneFromHealth(h.last_verification_passed !== false, h.verification_freshness_label === "stale")}
            hint="Ledger timestamp; freshness in control plane"
          />
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-stone-900">Connector health</h2>
            <p className="mt-1 text-sm text-stone-600">Where backlog and replay pressure concentrate.</p>
          </div>
          <Link className="text-sm font-medium text-indigo-700 hover:underline" to={overview}>
            Pipeline overview →
          </Link>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
                <th className="py-2 pr-4">Connector</th>
                <th className="py-2 pr-4">Raw</th>
                <th className="py-2 pr-4">Σ mat / pair (coverage)</th>
                <th className="py-2 pr-4">Untreated (routable gap)</th>
                <th className="py-2 pr-4">Replay failures (Σ)</th>
                <th className="py-2 pr-4">Coverage</th>
                <th className="py-2 pr-4">Last materialized</th>
                <th className="py-2 pr-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {connectorRows.map((r) => {
                const pct = r.coveragePct;
                const bad = r.replayFailures > 0 || r.hasDeadRoute;
                const warn = !bad && (r.untreatedRoutable > 0 || r.hasDormant);
                const tone = bad ? "bad" : warn ? "warn" : "ok";
                return (
                  <tr key={r.connector} className="border-b border-stone-100">
                    <td className="py-2 pr-4 font-medium text-stone-900">{titleConnector(r.connector)}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.rawRows.toLocaleString()}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.canonicalRows.toLocaleString()}</td>
                    <td className="py-2 pr-4 tabular-nums text-amber-900">{r.untreatedRoutable.toLocaleString()}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.replayFailures.toLocaleString()}</td>
                    <td className="py-2 pr-4 tabular-nums">{pct != null ? `${pct}%` : "—"}</td>
                    <td className="py-2 pr-4 text-xs text-stone-600">{r.lastMaterialized ? formatRelativeAge(r.lastMaterialized) : "—"}</td>
                    <td className="py-2 pr-2">
                      <StatusBadge tone={tone === "bad" ? "bad" : tone === "warn" ? "warn" : "ok"}>
                        {bad ? "action" : warn ? "watch" : "ok"}
                      </StatusBadge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Remediation</h2>
        <p className="mt-1 text-sm text-stone-600">
          Canonical materialization runs on the execution engine only. Use Overview → Start from step → Canonical
          (or Run from ingestion for a full refresh).
        </p>
        <Link
          className="mt-3 inline-block rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
          to={overview}
        >
          Open pipeline actions
        </Link>
      </section>

      <section className="rounded-xl border border-red-100 bg-red-50/30 p-5 shadow-sm ring-1 ring-red-100">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-red-950">Recent failure signals</h2>
          <span className="text-sm text-stone-500">Read-only registry slice</span>
        </div>
        {qFailures.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading failures…</p>
        ) : qFailures.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qFailures.error as Error).message}</p>
        ) : recentFailures.length === 0 ? (
          <p className="mt-2 text-sm text-stone-600">No active failure cases in registry.</p>
        ) : (
          <ul className="mt-3 divide-y divide-red-100 rounded-lg border border-red-100 bg-white text-sm">
            {recentFailures.map((x) => (
              <li key={x.gap_id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <div>
                  <span className="font-mono text-xs text-stone-500">{x.failure_class}</span>
                  <span className="mx-2 text-stone-300">·</span>
                  <span className="text-stone-800">{x.scope_kind}</span>
                  <p className="mt-0.5 text-xs text-stone-500">{x.source}</p>
                </div>
                <span className="shrink-0 text-xs text-stone-500">{x.degradation_state}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
