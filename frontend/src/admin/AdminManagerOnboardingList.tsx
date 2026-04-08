import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type SessionRow = {
  id: string;
  tenant_id: string;
  slack_team_id: string;
  slack_user_id: string;
  status: string;
  current_step: string;
  muted: boolean;
  updated_at: string | null;
  completed_at: string | null;
};

export default function AdminManagerOnboardingList() {
  const [sp] = useSearchParams();
  const tenantFilter = sp.get("tenant_id")?.trim() || "";
  const q = useQuery({
    queryKey: ["admin-mo-sessions", tenantFilter],
    queryFn: () => {
      const qs = tenantFilter ? `?tenant_id=${encodeURIComponent(tenantFilter)}&limit=200` : "?limit=200";
      return adminJson<{ items: SessionRow[] }>(`/admin/manager-onboarding/sessions${qs}`);
    },
  });

  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-stone-900">Manager Slack onboarding</h1>
          <p className="mt-1 text-sm text-stone-600">
            Sessions across tenants. Open a row for messages, answers, and operator actions.
          </p>
        </div>
        {tenantFilter ? (
          <Link
            to={`/admin/tenants/${tenantFilter}/manager-onboarding`}
            className="text-sm font-medium text-blue-700 underline"
          >
            ← Tenant hub
          </Link>
        ) : null}
      </div>

      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="data-table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Tenant</th>
              <th>Slack user</th>
              <th>Status</th>
              <th>Step</th>
              <th>Muted</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {q.data.items.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-stone-500">
                  No sessions
                </td>
              </tr>
            ) : (
              q.data.items.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link
                      to={`/admin/manager-onboarding/sessions/${s.id}`}
                      className="font-mono text-xs text-blue-700 underline"
                    >
                      {s.id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td>
                    <Link
                      to={`/admin/tenants/${s.tenant_id}/manager-onboarding`}
                      className="font-mono text-xs text-stone-700 underline"
                    >
                      {s.tenant_id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className="font-mono text-xs">{s.slack_user_id}</td>
                  <td>{s.status}</td>
                  <td className="text-xs">{s.current_step}</td>
                  <td>{s.muted ? "yes" : "—"}</td>
                  <td className="text-xs text-stone-600">
                    {s.updated_at ? new Date(s.updated_at).toLocaleString() : "—"}
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
