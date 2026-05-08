import { NavLink, Outlet, useParams } from "react-router-dom";

const CORTEX_SECTIONS: Array<{ key: string; label: string; enabled: boolean }> = [
  { key: "overview", label: "Overview", enabled: true },
  { key: "ingestion", label: "Ingestion", enabled: true },
  { key: "canonical", label: "Canonical", enabled: false },
  { key: "entity-resolution", label: "Entity Resolution", enabled: false },
  { key: "graph", label: "Graph", enabled: false },
  { key: "memory", label: "Memory", enabled: true },
  { key: "reasoning", label: "Reasoning", enabled: false },
  { key: "retrieval", label: "Retrieval", enabled: false },
  { key: "synthesis", label: "Synthesis", enabled: false },
  { key: "verification", label: "Verification", enabled: true },
  { key: "settings-debug", label: "Settings / Debug", enabled: false },
];

function tabCls(isActive: boolean, enabled: boolean): string {
  if (!enabled) {
    return "rounded-md border border-dashed border-stone-300 bg-stone-50 px-3 py-1.5 text-sm text-stone-400";
  }
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
        <h1 className="mt-1 text-xl font-semibold text-stone-900">Workspace Cortex Control Plane</h1>
        <p className="mt-1 text-sm text-stone-600">
          Tenant-scoped operational visibility and controls for ingestion and upcoming Cortex phases.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {CORTEX_SECTIONS.map((section) =>
          section.enabled ? (
            <NavLink
              key={section.key}
              to={`/admin/tenants/${tenantId}/cortex/${section.key}`}
              className={({ isActive }) => tabCls(isActive, true)}
            >
              {section.label}
            </NavLink>
          ) : (
            <span key={section.key} className={tabCls(false, false)} aria-disabled="true">
              {section.label}
            </span>
          ),
        )}
      </nav>

      <Outlet />
    </div>
  );
}
