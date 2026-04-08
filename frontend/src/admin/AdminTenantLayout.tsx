import { NavLink, Outlet, useParams } from "react-router-dom";

export default function AdminTenantLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const tabCls = ({ isActive }: { isActive: boolean }) =>
    [
      "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
      isActive
        ? "bg-stone-100 text-stone-900 ring-1 ring-inset ring-stone-200"
        : "text-stone-600 hover:bg-stone-50",
    ].join(" ");

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <nav className="mb-6 flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        <NavLink to={`/admin/tenants/${tenantId}/overview`} className={tabCls}>
          Overview
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/connections`} className={tabCls}>
          Connections
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/manager-onboarding`} className={tabCls}>
          Mgr Slack OB
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/step1`} className={tabCls}>
          Step1 Raw
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/step2`} className={tabCls}>
          Step2 Projections
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/step3`} className={tabCls}>
          Step3 Canonical
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
