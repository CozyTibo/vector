import { NavLink, Outlet, useParams } from "react-router-dom";

import { RETRIEVAL_NAV_SECTIONS } from "./retrievalAdminSurfaces";

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
      <p className="text-sm text-stone-600">
        Deterministic retrieval over lawful replay-safe reconstruction artifacts — not semantic search.
        Indexes chronology windows, causal chains, and continuity segments with full lineage visibility.
      </p>
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {RETRIEVAL_NAV_SECTIONS.map((s) => (
          <NavLink
            key={s.key || "overview"}
            to={s.key ? `${base}/${s.key}` : base}
            end={s.end}
            className={({ isActive }) => tabCls(isActive)}
          >
            {s.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
