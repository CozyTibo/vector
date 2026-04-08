import { NavLink, Outlet, useParams } from "react-router-dom";

/** Sub-navigation for raw → projections → canonical / graph tooling (nested under Data pipeline). */
export default function AdminTenantDataSectionLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const subTabCls = ({ isActive }: { isActive: boolean }) =>
    [
      "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
      isActive
        ? "bg-stone-200/90 text-stone-900 ring-1 ring-inset ring-stone-300/80"
        : "text-stone-600 hover:bg-stone-100 hover:text-stone-900",
    ].join(" ");

  return (
    <div>
      <nav
        aria-label="Data and pipeline tools"
        className="mb-6 flex flex-wrap gap-2 border-b border-stone-200 pb-3"
      >
        <NavLink
          to={`/admin/tenants/${tenantId}/data-pipeline`}
          end
          className={subTabCls}
        >
          Pipeline
        </NavLink>
        <NavLink
          to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph`}
          className={subTabCls}
        >
          Execution graph
        </NavLink>
        <NavLink to={`/admin/tenants/${tenantId}/data-pipeline/debug`} className={subTabCls}>
          Debug
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
