import { NavLink, Outlet, useParams } from "react-router-dom";

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-violet-100 text-violet-900 ring-1 ring-inset ring-violet-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexRetrievalLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/retrieval`;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">Retrieval indexes for query and synthesis. Rebuild via Overview → Start from step → Retrieval.</p>
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        <NavLink to={base} end className={({ isActive }) => tabCls(isActive)}>
          Summary
        </NavLink>
        <NavLink to={`${base}/index`} className={({ isActive }) => tabCls(isActive)}>
          Index
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
