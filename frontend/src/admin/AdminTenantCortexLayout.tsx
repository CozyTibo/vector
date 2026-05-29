import { NavLink, Outlet, useParams } from "react-router-dom";

import { IdentityPassStaleBadge } from "./cortex/IdentityPassStaleBadge";
import { useCortexPassRunHealth } from "./cortex/useCortexPassRunHealth";

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

function CortexNavTab({
  to,
  label,
  stale,
}: {
  to: string;
  label: string;
  stale: boolean;
}) {
  return (
    <NavLink to={to} className={({ isActive }) => tabCls(isActive)}>
      <span className="inline-flex items-center">
        {label}
        {stale ? <IdentityPassStaleBadge /> : null}
      </span>
    </NavLink>
  );
}

export default function AdminTenantCortexLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { ingestionStale, canonStale, identityStale } = useCortexPassRunHealth();

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Cortex</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">Cortex</h1>
        <p className="mt-1 text-sm text-stone-600">
          Raw ingestion and deterministic canon materialization for this workspace.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        <CortexNavTab
          to={`/admin/tenants/${tenantId}/cortex/ingestion`}
          label="Ingestion"
          stale={ingestionStale}
        />
        <CortexNavTab
          to={`/admin/tenants/${tenantId}/cortex/canon`}
          label="Canonical"
          stale={canonStale}
        />
        <CortexNavTab
          to={`/admin/tenants/${tenantId}/cortex/identities`}
          label="Identities"
          stale={identityStale}
        />
        <CortexNavTab
          to={`/admin/tenants/${tenantId}/cortex/declared-domains`}
          label="Declared Domains"
          stale={false}
        />
        <CortexNavTab
          to={`/admin/tenants/${tenantId}/cortex/links`}
          label="Links"
          stale={false}
        />
      </nav>

      <Outlet />
    </div>
  );
}
