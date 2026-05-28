import { useSearchParams } from "react-router-dom";

import { GraphDataTab } from "./cortex/GraphDataTab";
import { GraphRunsTab } from "./cortex/GraphRunsTab";
import { GraphStateTab } from "./cortex/GraphStateTab";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { IdentityPassStaleBadge } from "./cortex/IdentityPassStaleBadge";
import { useGraphReadiness } from "./cortex/useGraphReadiness";

type GraphTab = "state" | "runs" | "data";

function resolveTab(tabParam: string | null): GraphTab {
  if (tabParam === "runs") return "runs";
  if (tabParam === "data") return "data";
  if (tabParam === "links" || tabParam === "unresolved" || tabParam === "overview") return "data";
  return "state";
}

export default function AdminCortexGraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab = resolveTab(tabParam);
  const readinessQ = useGraphReadiness();
  const laneStale = Boolean(readinessQ.data?.scheduler?.lane_stale);

  const setTab = (next: GraphTab) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      if (next === "state") {
        p.delete("tab");
        p.delete("page");
        p.delete("view");
        p.delete("kind");
        p.delete("entity_id");
      } else if (next === "runs") {
        p.set("tab", "runs");
        p.delete("view");
        p.delete("kind");
        p.delete("entity_id");
      } else {
        p.set("tab", "data");
        if (tabParam === "unresolved") p.set("view", "unresolved");
        else if (!p.get("view")) p.delete("view");
      }
      return p;
    });
  };

  if (readinessQ.isLoading) {
    return <CortexPageSkeleton label="Loading graph projection" />;
  }
  if (readinessQ.isError) {
    return <p className="text-sm text-red-700">Failed to load graph readiness.</p>;
  }

  const data = readinessQ.data;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Links</h1>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic execution relationships projected from canon and provider evidence.
        </p>
        {data ? (
          <p className="mt-2 text-xs text-stone-500">
            Extractor v{data.extractor_version} · {data.active_relationship_count.toLocaleString()} active
            links · {data.dirty_queue_pending} dirty
            {data.graph_caught_up ? " · caught up" : null}
            {data.canon_backlog ? " · waiting on canon" : null}
          </p>
        ) : null}
      </header>

      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["state", "Overall state"],
            ["runs", "Runs"],
            ["data", "Data"],
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
            {key === "runs" && laneStale ? <IdentityPassStaleBadge /> : null}
          </button>
        ))}
      </nav>

      {tab === "state" ? <GraphStateTab /> : null}
      {tab === "runs" ? <GraphRunsTab /> : null}
      {tab === "data" ? <GraphDataTab /> : null}
    </div>
  );
}
