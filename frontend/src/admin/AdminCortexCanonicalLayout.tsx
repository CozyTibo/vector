import { NavLink, Outlet, useParams, useLocation } from "react-router-dom";

import { CanonicalOperatorFiltersProvider } from "./canonical/operatorFilters.tsx";

const PRIMARY_TABS: Array<{ to: string; label: string; end?: boolean }> = [
  { to: "health", label: "Health", end: true },
  { to: "coverage", label: "Coverage" },
  { to: "failures", label: "Failures" },
  { to: "advanced", label: "Advanced" },
];

function tabCls(isActive: boolean): string {
  return [
    "whitespace-nowrap rounded-md px-3 py-1.5 text-sm no-underline",
    isActive
      ? "bg-indigo-100 font-semibold text-indigo-900 ring-1 ring-inset ring-indigo-200"
      : "font-medium text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

export default function AdminCortexCanonicalLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const loc = useLocation();
  const base = `/admin/tenants/${tenantId}/cortex/canonical`;

  return (
    <CanonicalOperatorFiltersProvider>
      <div className="space-y-5">
        <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-700">Cortex · Canonical</p>
          <h1 className="mt-1 text-xl font-semibold text-stone-900">Execution substrate health</h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-600">
            Operator console: ingestion and canonicalization status, untreated backlog, failures, and fast
            remediation. Internal architecture and doctrine live under <span className="font-medium">Advanced</span>.
          </p>
        </header>

        <div className="-mx-1 overflow-x-auto pb-1">
          <nav className="flex min-w-min gap-1 rounded-xl border border-stone-200 bg-stone-50/90 p-2 shadow-inner">
            {PRIMARY_TABS.map((t) => (
              <NavLink
                key={t.to}
                end={t.end}
                to={`${base}/${t.to}`}
                className={({ isActive }) => tabCls(isActive)}
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <Outlet key={loc.pathname} />
      </div>
    </CanonicalOperatorFiltersProvider>
  );
}
