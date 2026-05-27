import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type TenantPause = {
  slack_vector_paused: boolean;
};

export default function AdminTenantLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const tenantQ = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminJson<TenantPause>(`/admin/tenants/${tenantId}`),
    enabled: Boolean(tenantId),
  });

  const tabCls = ({ isActive }: { isActive: boolean }) =>
    [
      "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
      isActive
        ? "bg-stone-100 text-stone-900 ring-1 ring-inset ring-stone-200"
        : "text-stone-600 hover:bg-stone-50",
    ].join(" ");

  const slackPaused = Boolean(tenantQ.data?.slack_vector_paused);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {slackPaused ? (
        <div
          role="alert"
          className="mb-4 rounded-lg border-2 border-amber-600 bg-amber-50 px-4 py-3 text-sm text-amber-950 shadow-sm"
        >
          <p className="font-semibold">Slack is paused for this entire workspace.</p>
          <p className="mt-1 text-amber-900/90">
            Vector will not send Slack DMs or replies for this company until you resume. Open the{" "}
            <Link
              to={`/admin/tenants/${tenantId}/workspace`}
              className="font-medium text-amber-950 underline decoration-amber-800 underline-offset-2"
            >
              Workspace
            </Link>{" "}
            tab to turn delivery back on.
          </p>
        </div>
      ) : null}

      <nav className="mb-6 flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        <NavLink to={`/admin/tenants/${tenantId}/workspace`} className={tabCls}>
          Workspace
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/onboarding`} className={tabCls}>
          Website onboarding
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/integrations`} className={tabCls}>
          Integrations
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/cortex/ingestion`} className={tabCls}>
          Cortex
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
