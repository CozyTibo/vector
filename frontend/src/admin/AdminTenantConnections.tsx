import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type Conn = { id: string; provider: string; status: string; created_at: string };

export default function AdminTenantConnections() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  const disconnectMut = useMutation({
    mutationFn: async (provider: string) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/connections/${encodeURIComponent(provider)}`, {
        method: "DELETE",
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-connections", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
    },
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
        OAuth only stores the link. Step 1 raw rows appear after{" "}
        <strong>sync</strong> (onboarding SCANNING or product/admin sync). View them under{" "}
        <Link to={`/admin/tenants/${tenantId}/step1`} className="text-blue-700 underline">
          Step1 Raw
        </Link>
        .
      </p>
      {disconnectMut.isError ? (
        <p className="mb-3 text-sm text-red-700">{(disconnectMut.error as Error).message}</p>
      ) : null}
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Status</th>
              <th>Connection ID</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {q.data.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-stone-500">
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
                  <td>
                    <button
                      type="button"
                      className="rounded border border-red-200 bg-white px-2.5 py-1 text-xs font-medium text-red-800 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={disconnectMut.isPending}
                      onClick={() => {
                        if (
                          !window.confirm(
                            `Disconnect ${c.provider} for this tenant? OAuth tokens and the link row are removed; ingestion data is not deleted.`,
                          )
                        ) {
                          return;
                        }
                        disconnectMut.mutate(c.provider);
                      }}
                    >
                      Disconnect
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
