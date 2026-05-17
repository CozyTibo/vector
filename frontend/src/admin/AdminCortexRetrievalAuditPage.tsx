import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type AuditRow = Record<string, unknown>;

export default function AdminCortexRetrievalAuditPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["retrieval-audit", tenantId],
    queryFn: () =>
      adminJson<{ audit_rows: AuditRow[] }>(
        `/admin/tenants/${tenantId}/cortex/retrieval/audit?limit=50`,
      ),
  });

  if (isLoading) return <p className="text-sm text-stone-500">Loading audit trail…</p>;
  if (!data) return null;

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Query audit trail</h2>
      <p className="mt-1 text-sm text-stone-600">Recent retrieval queries with legality class and replay pins.</p>
      {data.audit_rows.length === 0 ? (
        <p className="mt-3 text-sm text-stone-500">No audit rows yet.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="border-b border-stone-200 text-stone-600">
              <tr>
                <th className="py-2 pr-4">Recorded</th>
                <th className="py-2 pr-4">Workload</th>
                <th className="py-2 pr-4">Legality</th>
              </tr>
            </thead>
            <tbody>
              {data.audit_rows.map((row, i) => (
                <tr key={String(row.id ?? i)} className="border-b border-stone-100">
                  <td className="py-2 pr-4 font-mono">{String(row.created_at ?? "—")}</td>
                  <td className="py-2 pr-4">{String(row.workload_class ?? "—")}</td>
                  <td className="py-2 pr-4">{String(row.result_legality_class ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
