import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexRetrievalContinuityPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["continuity-topology", tenantId],
    queryFn: () =>
      adminJson<{
        continuity_posture: string;
        node_count: number;
        edge_count: number;
        nodes: unknown[];
        edges: unknown[];
      }>(`/admin/tenants/${tenantId}/cortex/retrieval/continuity-topology`),
  });

  if (isLoading) return <p className="text-sm text-stone-500">Loading…</p>;
  if (!data) return null;

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <h2 className="font-semibold text-stone-900">Continuity topology</h2>
        <StatusBadge tone={data.continuity_posture === "stable" ? "ok" : "warn"}>
          {data.continuity_posture}
        </StatusBadge>
      </div>
      <p className="mt-2 text-sm text-stone-600">
        {data.node_count} nodes, {data.edge_count} edges — ownership transfer and replay-conflict
        propagation (deterministic, not inferred).
      </p>
      <pre className="mt-3 max-h-80 overflow-auto rounded bg-stone-50 p-3 text-xs">
        {JSON.stringify(data, null, 2)}
      </pre>
    </section>
  );
}
