import { NavLink, Outlet, useParams } from "react-router-dom";

import { usePrefetchPipelineOverviewBootstrap } from "./cortex/usePipelineOverview";
import { isCortexAdminV2Enabled } from "./operator/featureFlags";

const CORTEX_SECTIONS: Array<{ key: string; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "ingestion", label: "Ingestion" },
  { key: "canonical", label: "Canonical" },
  { key: "identity", label: "Identity" },
  { key: "graph", label: "Graph" },
  { key: "reconstruction", label: "Reconstruction" },
  { key: "retrieval", label: "Retrieval" },
  { key: "synthesis", label: "Synthesis" },
  { key: "settings", label: "Settings" },
];

const CORTEX_V2_SECTIONS: Array<{ key: string; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "runtime", label: "Runtime" },
  { key: "queues", label: "Queues" },
  { key: "inspect", label: "Inspect" },
  { key: "ingestion", label: "Ingestion" },
  { key: "canonical", label: "Canonical" },
  { key: "reconstruction", label: "Reconstruction" },
  { key: "retrieval", label: "Retrieval" },
  { key: "synthesis", label: "Synthesis" },
  { key: "settings", label: "Settings" },
];

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
  usePrefetchPipelineOverviewBootstrap();
  const sections = isCortexAdminV2Enabled() ? CORTEX_V2_SECTIONS : CORTEX_SECTIONS;

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Cortex</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">Pipeline control panel</h1>
        <p className="mt-1 text-sm text-stone-600">
          Operator view: execution lease, phase status, and engine-only actions.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2 border-b border-stone-200 pb-3">
        {sections.map((section) => (
          <NavLink
            key={section.key}
            to={`/admin/tenants/${tenantId}/cortex/${section.key}`}
            className={({ isActive }) => tabCls(isActive)}
          >
            {section.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}
