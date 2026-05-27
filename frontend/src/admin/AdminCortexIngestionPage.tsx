import { useSearchParams } from "react-router-dom";

import { IngestionConnectorsTable } from "./cortex/IngestionConnectorsTable";
import { IngestionRunsTab } from "./cortex/IngestionRunsTab";
import { IngestionSchedulerPanel } from "./cortex/IngestionSchedulerPanel";
import { SectionSkeleton } from "./cortex/SectionSkeleton";
import { useCortexIngestionOverview } from "./cortex/useCortexIngestionOverview";

export default function AdminCortexIngestionPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "runs" ? "runs" : "connectors";
  const overviewQ = useCortexIngestionOverview();

  const setTab = (next: "connectors" | "runs") => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "runs") params.set("tab", "runs");
      else params.delete("tab");
      params.delete("page");
      return params;
    });
  };

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Ingestion</h1>
        <p className="mt-1 text-sm text-stone-600">
          Connector sync, raw storage, and ingestion scheduler for this workspace.
        </p>
        {overviewQ.data?.digest?.bottleneck ? (
          <p className="mt-2 text-sm text-amber-800">{overviewQ.data.digest.bottleneck}</p>
        ) : null}
      </header>

      <IngestionSchedulerPanel overview={overviewQ.data} />

      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["connectors", "Connectors"],
            ["runs", "Runs"],
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
          </button>
        ))}
      </nav>

      {tab === "connectors" ? (
        overviewQ.isPending && !overviewQ.data ? (
          <SectionSkeleton variant="table" />
        ) : (
          <IngestionConnectorsTable connectors={overviewQ.data?.connectors ?? []} />
        )
      ) : (
        <IngestionRunsTab />
      )}
    </div>
  );
}
