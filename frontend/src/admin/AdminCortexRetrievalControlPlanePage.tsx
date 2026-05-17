import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type Surface = {
  surface_number: number;
  surface_id: string;
  label: string;
  wired_at_closure: boolean;
  closure_step: number;
  admin_routes: string[];
};

type ControlPlane = {
  gate_id: string;
  surfaces_total: number;
  surfaces_wired_count: number;
  surface_checklist: Surface[];
  workload_histogram: Record<string, number>;
  openapi_path_count: number;
};

export default function AdminCortexRetrievalControlPlanePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["retrieval-control-plane", tenantId],
    queryFn: () =>
      adminJson<ControlPlane>(`/admin/tenants/${tenantId}/cortex/retrieval/control-plane`),
  });

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Retrieval control plane</h2>
        {isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {data && (
          <>
            <p className="mt-2 text-sm text-stone-600">
              {data.surfaces_wired_count} / {data.surfaces_total} surfaces wired ·{" "}
              {data.openapi_path_count} OpenAPI admin paths · gate {data.gate_id}
            </p>
            <table className="mt-4 w-full text-left text-sm">
              <thead>
                <tr className="border-b border-stone-200 text-stone-500">
                  <th className="py-1 pr-2">#</th>
                  <th className="py-1 pr-2">Surface</th>
                  <th className="py-1 pr-2">Step</th>
                  <th className="py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.surface_checklist.map((s) => (
                  <tr key={s.surface_id} className="border-b border-stone-100">
                    <td className="py-2 pr-2 font-mono text-xs">{s.surface_number}</td>
                    <td className="py-2 pr-2">
                      <div className="font-medium text-stone-900">{s.label}</div>
                      <div className="font-mono text-xs text-stone-500">{s.surface_id}</div>
                    </td>
                    <td className="py-2 pr-2 text-xs">P07-{s.closure_step}</td>
                    <td className="py-2">
                      <StatusBadge tone={s.wired_at_closure ? "ok" : "warn"}>
                        {s.wired_at_closure ? "wired" : "planned"}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <h3 className="mt-4 text-sm font-semibold text-stone-800">Workload histogram</h3>
            <pre className="mt-1 max-h-40 overflow-auto rounded border border-stone-200 bg-stone-50 p-2 text-xs">
              {JSON.stringify(data.workload_histogram, null, 2)}
            </pre>
          </>
        )}
      </section>
    </div>
  );
}
