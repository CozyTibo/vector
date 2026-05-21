import { Outlet, useParams } from "react-router-dom";

import { CanonicalOperatorFiltersProvider } from "./canonical/operatorFilters.tsx";

export default function AdminCortexCanonicalLayout() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  return (
    <CanonicalOperatorFiltersProvider>
      <div className="space-y-5">
        <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-700">Cortex · Canonical</p>
          <h1 className="mt-1 text-xl font-semibold text-stone-900">Canonical substrate</h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-600">
            Raw → deterministic canonical rows. Progression is driven by the{" "}
            <a
              href={`/admin/tenants/${tenantId}/cortex/overview`}
              className="font-medium text-indigo-700 underline"
            >
              execution engine
            </a>
            ; use Overview to run or unblock.
          </p>
        </header>
        <Outlet />
      </div>
    </CanonicalOperatorFiltersProvider>
  );
}
