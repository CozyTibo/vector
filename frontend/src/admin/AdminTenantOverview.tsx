import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type OnboardingSnap = {
  status: string;
  current_step: string;
  started_at: string | null;
  completed_at: string | null;
  abandoned_at: string | null;
  tools_interest: string[];
  company_domain: string | null;
  tools_stack: Record<string, unknown> | null;
};

type TenantDetail = {
  id: string;
  company_name: string;
  created_at: string;
  onboarding: OnboardingSnap | null;
  connected_connectors: string[];
};

export default function AdminTenantOverview() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminJson<TenantDetail>(`/admin/tenants/${tenantId}`),
    enabled: Boolean(tenantId),
  });

  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const t = q.data;
  const ob = t.onboarding;
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-stone-900">{t.company_name}</h2>
        <dl className="grid max-w-md grid-cols-[auto_1fr] gap-2 text-sm">
          <dt className="text-stone-500">Tenant ID</dt>
          <dd className="font-mono text-stone-800">{t.id}</dd>
          <dt className="text-stone-500">Created</dt>
          <dd>{new Date(t.created_at).toLocaleString()}</dd>
          <dt className="text-stone-500">Connectors</dt>
          <dd>{t.connected_connectors.length ? t.connected_connectors.join(", ") : "—"}</dd>
        </dl>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="mb-3 text-base font-semibold text-stone-900">Onboarding</h3>
        {ob ? (
          <dl className="grid max-w-lg grid-cols-[auto_1fr] gap-2 text-sm">
            <dt className="text-stone-500">Status</dt>
            <dd className="text-stone-800">{ob.status}</dd>
            <dt className="text-stone-500">Current step</dt>
            <dd className="text-stone-800">{ob.current_step}</dd>
            <dt className="text-stone-500">Started</dt>
            <dd>{ob.started_at ? new Date(ob.started_at).toLocaleString() : "—"}</dd>
            <dt className="text-stone-500">Completed</dt>
            <dd>{ob.completed_at ? new Date(ob.completed_at).toLocaleString() : "—"}</dd>
            <dt className="text-stone-500">Abandoned</dt>
            <dd>{ob.abandoned_at ? new Date(ob.abandoned_at).toLocaleString() : "—"}</dd>
            <dt className="text-stone-500">Tools interest</dt>
            <dd>{ob.tools_interest.length ? ob.tools_interest.join(", ") : "—"}</dd>
            <dt className="text-stone-500">Company domain (answers)</dt>
            <dd>{ob.company_domain ?? "—"}</dd>
            <dt className="text-stone-500">Tools stack (research)</dt>
            <dd className="min-w-0">
              {ob.tools_stack && Object.keys(ob.tools_stack).length > 0 ? (
                <pre className="mt-1 max-h-64 overflow-auto rounded-md bg-stone-50 p-3 text-xs text-stone-800 whitespace-pre-wrap break-words">
                  {JSON.stringify(ob.tools_stack, null, 2)}
                </pre>
              ) : (
                "—"
              )}
            </dd>
          </dl>
        ) : (
          <p className="text-sm text-stone-600">No onboarding row yet (tenant never opened product onboarding).</p>
        )}
      </div>
    </div>
  );
}
