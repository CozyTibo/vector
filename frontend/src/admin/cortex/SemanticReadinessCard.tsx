import type { SemanticOperatorMetric, SemanticReadiness } from "./pipelineTypes";
import { StatusBadge } from "../ui/StatusBadge";
import { SectionSkeleton } from "./SectionSkeleton";

function severityTone(sev: string | undefined): "ok" | "warn" | "bad" {
  if (sev === "ok") return "ok";
  if (sev === "bad") return "bad";
  return "warn";
}

function formatMetricValue(metric: SemanticOperatorMetric): string {
  const v = metric.value;
  if (v == null) return "—";
  if (metric.key === "retrieval_freshness_minutes") return `${v} min`;
  if (metric.key.endsWith("_pct")) return `${v}%`;
  if (typeof v === "number") return v.toLocaleString();
  return String(v);
}

export function SemanticReadinessCard({
  data,
  loading,
}: {
  data: SemanticReadiness | null | undefined;
  loading?: boolean;
}) {
  if (loading && !data) {
    return (
      <section className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-5 shadow-sm">
        <SectionSkeleton variant="cards" />
      </section>
    );
  }
  if (!data) return null;

  const g = data.graph_truth;
  const ic = data.identity_continuity;
  const r = data.retrieval;
  const s = data.synthesis;
  const panel =
    data.semantic_operator_panel && data.semantic_operator_panel.length > 0
      ? data.semantic_operator_panel
      : null;

  return (
    <section className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">Semantic readiness</h2>
          <p className="mt-1 text-sm text-stone-600">
            Semantic track — pair with continuity overview (runtime track). M3/AA PASS ≠ semantic green.
          </p>
        </div>
        <StatusBadge tone={severityTone(g.dup_factor_severity)}>
          dup {g.dup_factor ?? "—"}
        </StatusBadge>
      </div>

      {crossCheck?.rule_active ? (
        <motion.div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          {crossCheck.operator_message ??
            "Runtime AA/M3 PASS does not imply semantic green — check graph truth and retrieval mix."}
        </motion.div>
      ) : null}

      {inspection ? (
        <details className="mt-4 rounded-lg border border-emerald-200 bg-white p-3 text-sm" open>
          <summary className="cursor-pointer font-medium text-emerald-950">
            Execution reality inspection
          </summary>
          <div className="mt-3 grid gap-4 lg:grid-cols-2">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Identity continuity
              </h4>
              <p className="mt-1 text-stone-800">
                Distinct pairs{" "}
                {inspection.identity_continuity?.distinct_candidate_pairs?.toLocaleString() ?? "—"} ·
                inflation {String(inspection.identity_continuity?.candidate_inflation_ratio ?? "—")}
              </p>
            </div>
            <motion.div>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {panel.map((metric) => (
            <div
              key={metric.key}
              className="rounded-lg border border-emerald-100 bg-white p-3 shadow-sm"
            >
              <dt className="text-xs font-medium uppercase tracking-wide text-emerald-900">
                {metric.label}
              </dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <span className="text-xl font-semibold tabular-nums text-emerald-950">
                  {formatMetricValue(metric)}
                </span>
                {metric.severity ? (
                  <StatusBadge tone={severityTone(metric.severity)}>{metric.severity}</StatusBadge>
                ) : null}
              </dd>
              {metric.green_rule ? (
                <p className="mt-1 text-xs text-stone-500">Green: {metric.green_rule}</p>
              ) : null}
            </div>
          ))}
        </dl>
      ) : null}

      <details className="mt-4 rounded-lg border border-stone-200 bg-white/80 p-3 text-sm">
        <summary className="cursor-pointer font-medium text-stone-800">Diagnostic detail</summary>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border border-stone-100 p-3">
            <dt className="text-xs uppercase text-stone-500">Auth edge rows (diagnostic)</dt>
            <dd className="mt-1 tabular-nums font-semibold">{g.auth_edge_rows.toLocaleString()}</dd>
          </div>
          {ic ? (
            <>
              <div className="rounded-lg border border-stone-100 p-3">
                <dt className="text-xs uppercase text-stone-500">Distinct candidate pairs</dt>
                <dd className="mt-1 tabular-nums font-semibold">
                  {ic.distinct_candidate_pairs?.toLocaleString() ?? "—"}
                </dd>
                <p className="mt-1 text-xs text-stone-500">
                  Rows {ic.candidate_rows?.toLocaleString() ?? "—"} (diagnostic)
                </p>
              </div>
              <div className="rounded-lg border border-stone-100 p-3">
                <dt className="text-xs uppercase text-stone-500">Anchors missing org entity</dt>
                <dd className="mt-1 tabular-nums font-semibold">
                  {ic.anchors_missing_org_entity_pct ?? "—"}%
                </dd>
              </div>
            </>
          ) : null}
          <div className="rounded-lg border border-stone-100 p-3">
            <dt className="text-xs uppercase text-stone-500">Entities in auth graph</dt>
            <dd className="mt-1 tabular-nums font-semibold">{g.entities_in_auth_graph_pct}%</dd>
          </div>
          <div className="rounded-lg border border-stone-100 p-3">
            <dt className="text-xs uppercase text-stone-500">Published claims (7d)</dt>
            <dd className="mt-1 tabular-nums font-semibold">{s.published_claims_7d ?? "—"}</dd>
          </div>
          <div className="rounded-lg border border-stone-100 p-3">
            <dt className="text-xs uppercase text-stone-500">Published epoch</dt>
            <dd className="mt-1 font-mono text-xs text-stone-700">{r.published_index_epoch ?? "—"}</dd>
          </div>
        </dl>

        {g.promotions_by_rule_id.length > 0 ? (
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-stone-200 bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-3 py-2 font-medium">rule_id</th>
                  <th className="px-3 py-2 font-medium">unique pairs</th>
                  <th className="px-3 py-2 font-medium">rows (dup diagnostic)</th>
                </tr>
              </thead>
              <tbody>
                {g.promotions_by_rule_id.map((row) => (
                  <tr key={row.rule_id} className="border-b border-stone-100 last:border-0">
                    <td className="px-3 py-2 font-mono text-xs">{row.rule_id}</td>
                    <td className="px-3 py-2 tabular-nums">{row.unique_pairs.toLocaleString()}</td>
                    <td className="px-3 py-2 tabular-nums text-stone-500">
                      {row.auth_edge_rows.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </details>
    </section>
  );
}
