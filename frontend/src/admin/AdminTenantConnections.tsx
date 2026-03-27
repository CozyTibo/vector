import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type Conn = { id: string; provider: string; status: string; created_at: string };

export default function AdminTenantConnections() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  return (
    <div>
      <p className="mb-4 text-sm text-stone-600">
        Raw GitHub ingestion rows for this tenant are under{" "}
        <Link to={`/admin/tenants/${tenantId}/step1`} className="text-blue-700 underline">
          Step1 Raw
        </Link>
        .
      </p>
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
      <table className="data-table">
        <thead>
          <tr>
            <th>Provider</th>
            <th>Status</th>
            <th>Connection ID</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {q.data.items.length === 0 ? (
            <tr>
              <td colSpan={4} className="text-stone-500">
                No connections
              </td>
            </tr>
          ) : (
            q.data.items.map((c) => (
              <tr key={c.id}>
                <td>{c.provider}</td>
                <td>{c.status}</td>
                <td className="font-mono text-xs">{c.id}</td>
                <td>{new Date(c.created_at).toLocaleString()}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      </div>
    </div>
  );
}
