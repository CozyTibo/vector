import { NavLink, Outlet, useParams } from "react-router-dom";

import { SYNTHESIS_NAV_SECTIONS } from "./synthesisAdminSurfaces";

function tabCls(isActive: boolean): string {
  return [
    "rounded-md px-3 py-1.5 text-sm font-medium no-underline",
    isActive
      ? "bg-violet-100 text-violet-900 ring-1 ring-inset ring-violet-200"
      : "text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexSynthesisLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/synthesis`;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        Synthesis &amp; Intelligence Layer — deterministic intelligence artifacts over lawful retrieval
        evidence. Not free-form summarization; every claim is cite-or-omit with replay-safe receipts.
      </p>
      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {SYNTHESIS_NAV_SECTIONS.map((s) => (
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
