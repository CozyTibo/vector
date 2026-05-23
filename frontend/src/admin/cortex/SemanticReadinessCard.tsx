import type { SemanticReadiness } from "./pipelineTypes";
import { StatusBadge } from "../ui/StatusBadge";
import { SectionSkeleton } from "./SectionSkeleton";

function severityTone(sev: string | undefined): "ok" | "warn" | "bad" {
  if (sev === "ok") return "ok";
  if (sev === "bad") return "bad";
  return "warn";
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
  const r = data.retrieval;
  const s = data.synthesis;

  return (
    <section className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">Semantic readiness</h2>
          <p className="mt-1 text-sm text-stone-600">
            Product substrate: <strong className="font-medium">{data.product_substrate}</strong> — graph
            supports retrieval; retrieval grounds synthesis. Not raw link row counts.
          </p>
        </div>
        <StatusBadge tone={severityTone(g.dup_factor_severity)}>
          dup {g.dup_factor ?? "—"}
        </StatusBadge>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-emerald-100 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-emerald-900">
            Unique auth pairs (primary)
          </dt>
          <dd className="mt-1 text-xl font-semibold tabular-nums text-emerald-950">
            {g.unique_auth_pairs.toLocaleString()}
          </dd>
          <p className="mt-1 text-xs text-stone-500">
            Row count {g.auth_edge_rows.toLocaleString()} (diagnostic only)
          </p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Promotion rules (with edges)
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{g.promotion_rule_count}</dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Entities in auth graph
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">
            {g.entities_in_auth_graph_pct}%
          </dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Retrieval org_link %
          </dt>
          <dd className="mt-1 flex items-center gap-2">
            <span className="text-lg font-semibold tabular-nums">{r.org_link_pct ?? "—"}%</span>
            {r.org_link_pct_severity ? (
              <StatusBadge tone={severityTone(r.org_link_pct_severity)}>{r.org_link_pct_severity}</StatusBadge>
            ) : null}
          </dd>
          <p className="mt-1 text-xs text-stone-500">Target ≤30% (execution index kinds dominate)</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Retrieval execution index %
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{r.execution_index_pct ?? "—"}%</dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Synthesis artifacts with claims
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{s.artifacts_with_claims}</dd>
        </div>
      </dl>

      {g.promotions_by_rule_id.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200 bg-white">
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
    </section>
  );
}
