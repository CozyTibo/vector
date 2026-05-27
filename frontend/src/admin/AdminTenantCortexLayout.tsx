import { NavLink, Outlet, useParams } from "react-router-dom";

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminTenantCortexLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

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
        <NavLink
          to={`/admin/tenants/${tenantId}/cortex/ingestion`}
          className={({ isActive }) => tabCls(isActive)}
        >
          Ingestion
        </NavLink>
        <NavLink
          to={`/admin/tenants/${tenantId}/cortex/canon`}
          className={({ isActive }) => tabCls(isActive)}
        >
          Canon
        </NavLink>
      </nav>

      <Outlet />
    </div>
  );
}
