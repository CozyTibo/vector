import { useSearchParams } from "react-router-dom";

import { CanonConnectorsCoverageTab } from "./cortex/CanonConnectorsCoverageTab";
import { CanonEntitiesListingTab } from "./cortex/CanonEntitiesListingTab";
import { CanonRunsTab } from "./cortex/CanonRunsTab";
import { CanonSchedulerPanel } from "./cortex/CanonSchedulerPanel";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { IdentityPassStaleBadge } from "./cortex/IdentityPassStaleBadge";
import { useCanonReadiness } from "./cortex/useCanonReadiness";
import { useCortexPassRunHealth } from "./cortex/useCortexPassRunHealth";

export default function AdminCortexCanonPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab =
    tabParam === "entities" ? "entities" : tabParam === "runs" ? "runs" : "connectors";
  const readinessQ = useCanonReadiness();
  const { canonStale: passRunStale } = useCortexPassRunHealth();

  const setTab = (next: "connectors" | "runs" | "entities") => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "connectors") params.delete("tab");
      else params.set("tab", next);
      params.delete("canon_page");
      params.delete("page");
      return params;
    });
  };

  if (readinessQ.isLoading) {
    return <CortexPageSkeleton label="Loading canonical materialization" />;
  }
  if (readinessQ.isError) {
    return <p className="text-sm text-red-700">Failed to load canon readiness.</p>;
  }

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Canonical</h1>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic canon materialization from raw exhaust — coverage gaps and entity listing.
        </p>
        {readinessQ.data ? (
          <p className="mt-2 text-xs text-stone-500">
            Mapper v{readinessQ.data.mapper_version} · {readinessQ.data.raw_inventory.total_live_rows.toLocaleString()}{" "}
            live raw rows · {readinessQ.data.dirty_queue_depth} queued
          </p>
        ) : null}
      </header>

      <CanonSchedulerPanel />

      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["connectors", "Per connector"],
            ["runs", "Runs"],
            ["entities", "Entities by type"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={[
              "rounded-md px-3 py-1.5 text-sm font-medium",
              tab === key
                ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                : "text-stone-700 hover:bg-stone-100",
            ].join(" ")}
            onClick={() => setTab(key)}
          >
            {label}
            {key === "runs" && passRunStale ? <IdentityPassStaleBadge /> : null}
          </button>
        ))}
      </nav>

      {tab === "connectors" ? (
        <CanonConnectorsCoverageTab />
      ) : tab === "runs" ? (
        <CanonRunsTab />
      ) : (
        <CanonEntitiesListingTab />
      )}
    </div>
  );
}
