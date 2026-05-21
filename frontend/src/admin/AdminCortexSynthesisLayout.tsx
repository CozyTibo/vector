import { NavLink, Outlet, useParams } from "react-router-dom";

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-emerald-100 text-emerald-900 ring-1 ring-inset ring-emerald-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexSynthesisLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/synthesis`;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">Synthesis artifacts. Activation is owned by execution phase 08.</p>
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        <NavLink to={base} end className={({ isActive }) => tabCls(isActive)}>
          Summary
        </NavLink>
        <NavLink to={`${base}/jobs`} className={({ isActive }) => tabCls(isActive)}>
          Jobs
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
