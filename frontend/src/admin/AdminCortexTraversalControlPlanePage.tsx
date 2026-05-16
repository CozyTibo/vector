import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type ControlPlane = {
  tenant_id: string;
  traversal_queue: Array<Record<string, unknown>>;
  abort_classes: Record<string, number>;
  budget_histogram: Record<string, number>;
  computed_at_utc: string;
  include_exploration: boolean;
  t_as_of_unix_ns?: number | null;
};

export default function AdminCortexTraversalControlPlanePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["octs-control-plane-full", tenantId],
    queryFn: () =>
      adminJson<ControlPlane>(
        `/admin/tenants/${tenantId}/cortex/traversal/control-plane?include_exploration=1`,
      ),
  });

  if (isLoading) return <p className="text-sm text-stone-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{(error as Error).message}</p>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Structural control plane</h2>
        <p className="mt-1 text-xs text-stone-500">
          Computed {data.computed_at_utc}
          {data.t_as_of_unix_ns != null ? ` · t_as_of ${data.t_as_of_unix_ns}` : ""}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge tone={data.include_exploration ? "neutral" : "ok"}>
            exploration {data.include_exploration ? "included" : "hidden"}
          </StatusBadge>
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold text-stone-900">Traversal queue ({data.traversal_queue.length})</h3>
        {data.traversal_queue.length === 0 ? (
          <p className="mt-2 text-sm text-stone-500">No walks recorded for this tenant.</p>
        ) : (
          <pre className="mt-2 max-h-96 overflow-auto rounded bg-stone-50 p-3 text-xs">
            {JSON.stringify(data.traversal_queue, null, 2)}
          </pre>
        )}
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h3 className="font-semibold text-stone-900">Abort classes</h3>
          <pre className="mt-2 text-xs">{JSON.stringify(data.abort_classes, null, 2)}</pre>
        </section>
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h3 className="font-semibold text-stone-900">Budget histogram</h3>
          <pre className="mt-2 text-xs">{JSON.stringify(data.budget_histogram, null, 2)}</pre>
        </section>
      </div>
    </div>
  );
}
