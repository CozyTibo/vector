import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type EngineIdentity = {
  engine_identity_available: boolean;
  engine_build_id: string | null;
  error_code?: string;
};

type ControlPlane = {
  tenant_id: string;
  traversal_queue: Array<{ walk_id: string; status: string; execution_partition?: string }>;
  abort_classes: Record<string, number>;
  budget_histogram: Record<string, number>;
  computed_at_utc: string;
  include_exploration: boolean;
};

export default function AdminCortexTraversalOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/traversal`;

  const engineQ = useQuery({
    queryKey: ["octs-engine-identity", tenantId],
    queryFn: () =>
      adminJson<EngineIdentity>(`/admin/tenants/${tenantId}/cortex/traversal/engine-identity`),
  });

  const cpQ = useQuery({
    queryKey: ["octs-control-plane", tenantId],
    queryFn: () =>
      adminJson<ControlPlane>(`/admin/tenants/${tenantId}/cortex/traversal/control-plane`),
  });

  const engine = engineQ.data;
  const cp = cpQ.data;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Engine identity</h2>
        {engineQ.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {engine && (
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-stone-500">Available</dt>
              <dd>
                <StatusBadge tone={engine.engine_identity_available ? "ok" : "warn"}>
                  {engine.engine_identity_available ? "yes" : "no"}
                </StatusBadge>
              </dd>
            </div>
            <div>
              <dt className="text-stone-500">Build id</dt>
              <dd className="font-mono text-xs">{engine.engine_build_id ?? "—"}</dd>
            </div>
            {engine.error_code && (
              <div className="sm:col-span-2">
                <dt className="text-stone-500">Error</dt>
                <dd className="text-amber-800">{engine.error_code}</dd>
              </div>
            )}
          </dl>
        )}
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-stone-900">Traversal queue snapshot</h2>
          <Link to={`${base}/control-plane`} className="text-sm text-indigo-700 underline">
            Full control plane
          </Link>
        </div>
        {cpQ.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {cp && (
          <>
            <p className="mt-1 text-xs text-stone-500">Computed {cp.computed_at_utc}</p>
            <p className="mt-3 text-2xl font-semibold">{cp.traversal_queue.length}</p>
            <p className="text-xs text-stone-500">walks in queue listing</p>
            {Object.keys(cp.abort_classes).length > 0 && (
              <ul className="mt-3 text-xs text-amber-900">
                {Object.entries(cp.abort_classes).map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </div>
  );
}
