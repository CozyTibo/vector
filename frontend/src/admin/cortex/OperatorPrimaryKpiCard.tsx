import type { OperatorPrimaryKpi } from "./pipelineTypes";
import { StatusBadge } from "../ui/StatusBadge";
import { SectionSkeleton } from "./SectionSkeleton";

function metricTone(value: number): "ok" | "warn" | "bad" {
  if (value <= 0) return "ok";
  if (value < 500) return "warn";
  return "bad";
}

export function OperatorPrimaryKpiCard({
  kpi,
  loading,
}: {
  kpi: OperatorPrimaryKpi | undefined;
  loading?: boolean;
}) {
  if (loading && !kpi) {
    return (
      <section className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-5 shadow-sm">
        <SectionSkeleton variant="cards" />
      </section>
    );
  }
  if (!kpi) return null;

  const drainable = Number(kpi.drainable_routable_estimate ?? 0);
  const untreated = Number(kpi.untreated_routable_estimate ?? 0);
  const rawGap = Number(kpi.raw_minus_mat_admin_gap ?? 0);
  const islands = kpi.execution_islands ?? [];

  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">Operator primary KPI</h2>
          <p className="mt-1 text-sm text-stone-600">
            Drainable routable backlog and execution islands — not raw−materialized vanity gap.
          </p>
        </div>
        <StatusBadge tone={metricTone(drainable)}>
          Drainable {drainable.toLocaleString()}
        </StatusBadge>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-indigo-100 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-indigo-800">
            Drainable routable
          </dt>
          <dd className="mt-1 text-xl font-semibold tabular-nums text-indigo-950">
            {drainable.toLocaleString()}
          </dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Untreated routable
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-stone-900">
            {untreated.toLocaleString()}
          </dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white/80 p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-400">
            Raw−mat gap (diagnostic)
          </dt>
          <dd className="mt-1 text-sm tabular-nums text-stone-600">{rawGap.toLocaleString()}</dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Execution islands
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-stone-900">
            {Number(kpi.execution_island_count ?? islands.length).toLocaleString()}
            {!kpi.execution_island_registry_enabled ? (
              <span className="block text-xs font-normal text-stone-500">registry off</span>
            ) : null}
          </dd>
        </div>
      </dl>

      {islands.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200 bg-white">
          <table className="min-w-full text-xs">
            <thead className="bg-stone-50 text-left text-stone-700">
              <tr>
                <th className="px-3 py-2">Island scope</th>
                <th className="px-3 py-2">Entities</th>
                <th className="px-3 py-2">Auth edges</th>
                <th className="px-3 py-2">Last retrieval epoch</th>
              </tr>
            </thead>
            <tbody>
              {islands.map((row) => (
                <tr key={row.island_scope_id} className="border-t border-stone-100">
                  <td className="max-w-[14rem] truncate px-3 py-2 font-mono text-[11px]">
                    {row.island_scope_id}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{row.entity_count.toLocaleString()}</td>
                  <td className="px-3 py-2 tabular-nums">
                    {row.authoritative_edge_count.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-stone-600">{row.last_retrieval_epoch ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-3 text-sm text-stone-500">No persisted execution islands for this tenant yet.</p>
      )}
    </section>
  );
}
