import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type TenantRow = {
  id: string;
  company_name: string;
  created_at: string;
  onboarding_status: string | null;
  onboarding_current_step: string | null;
  connected_connectors: string[];
};

export default function AdminTenantsPage() {
  const q = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => adminJson<{ items: TenantRow[] }>("/admin/tenants"),
  });

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-xl font-semibold text-stone-900">Tenants</h1>
      {q.isPending ? <p className="text-sm text-stone-600">Loading…</p> : null}
      {q.isError ? (
        <p className="text-sm text-red-700">{(q.error as Error).message}</p>
      ) : null}
      {q.data ? (
        <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
          <table className="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Onboarding</th>
                <th>Connectors</th>
                <th>ID</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-stone-500">
                    No tenants
                  </td>
                </tr>
              ) : (
                q.data.items.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <Link
                        to={`/admin/tenants/${t.id}/overview`}
                        className="font-medium text-blue-700 underline"
                      >
                        {t.company_name}
                      </Link>
                    </td>
                    <td className="text-sm text-stone-700">
                      {t.onboarding_status ?? "—"}
                      {t.onboarding_current_step ? (
                        <span className="block text-xs text-stone-500">{t.onboarding_current_step}</span>
                      ) : null}
                    </td>
                    <td className="text-sm text-stone-700">
                      {t.connected_connectors.length ? t.connected_connectors.join(", ") : "—"}
                    </td>
                    <td className="font-mono text-xs text-stone-600">{t.id}</td>
                    <td className="text-sm text-stone-700">
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </main>
  );
}
