import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import type { CanonPassRunItem, CanonReadiness } from "./cortexAdminTypes";
import { useCanonReadiness } from "./cortex/useCanonReadiness";
import CortexPageSkeleton from "./cortex/CortexPageSkeleton";

export default function AdminCortexCanonPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const readinessQ = useCanonReadiness();
  const passesQ = useQuery({
    queryKey: ["admin-cortex-canon-passes", tenantId],
    queryFn: () =>
      adminJson<{ items: CanonPassRunItem[]; total_count: number }>(
        `/admin/tenants/${tenantId}/cortex/canon/recent-passes?limit=20`,
      ),
    enabled: Boolean(tenantId),
  });

  if (readinessQ.isLoading) {
    return <CortexPageSkeleton />;
  }
  if (readinessQ.isError || !readinessQ.data) {
    return (
      <p className="text-sm text-red-700">Failed to load canon readiness.</p>
    );
  }

  const data: CanonReadiness = readinessQ.data;
  const inv = data.raw_inventory;
  const lag = data.materialization_lag;
  const cls = data.resource_type_classification;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Canon readiness</h2>
        <p className="mt-1 text-sm text-stone-600">
          Mapper v{data.mapper_version} · scheduler{" "}
          {data.scheduler.enabled ? "on" : "off"} ({data.scheduler.interval_seconds}s)
        </p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-xs font-medium uppercase text-stone-500">Live raw rows</dt>
            <dd className="text-lg font-semibold text-stone-900">{inv.total_live_rows}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-stone-500">Lineage identities</dt>
            <dd className="text-lg font-semibold text-stone-900">{inv.lineage_identity_count}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-stone-500">Pending raw (est.)</dt>
            <dd className="text-lg font-semibold text-stone-900">
              {lag.pending_raw_rows_estimate}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-stone-500">Dirty queue</dt>
            <dd className="text-lg font-semibold text-stone-900">{data.dirty_queue_depth}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-stone-900">Resource types</h3>
        <p className="mt-1 text-sm text-stone-600">
          Mapped: {cls.mapped.length} · Unknown: {cls.unknown.length} · Skipped: {cls.skipped.length}
        </p>
        <ul className="mt-3 max-h-48 overflow-y-auto text-sm text-stone-800">
          {Object.entries(inv.resource_type_counts).map(([rt, n]) => (
            <li key={rt} className="flex justify-between border-b border-stone-100 py-1">
              <span className="font-mono text-xs">{rt}</span>
              <span>{n}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-stone-900">Recent passes</h3>
        {passesQ.isLoading ? (
          <p className="mt-2 text-sm text-stone-500">Loading…</p>
        ) : (
          <ul className="mt-2 space-y-2 text-sm">
            {(passesQ.data?.items ?? []).length === 0 ? (
              <li className="text-stone-500">No canon passes yet.</li>
            ) : (
              passesQ.data?.items.map((p) => (
                <li key={p.id} className="rounded border border-stone-100 px-3 py-2">
                  <span className="font-medium">{p.status}</span>
                  <span className="text-stone-500"> · {p.source_trigger}</span>
                  <span className="block text-xs text-stone-500">{p.started_at}</span>
                </li>
              ))
            )}
          </ul>
        )}
      </section>
    </div>
  );
}
