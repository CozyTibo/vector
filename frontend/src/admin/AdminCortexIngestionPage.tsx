import { Link, useParams, useSearchParams } from "react-router-dom";

import { IngestionRunsTab } from "./cortex/IngestionRunsTab";
import { SectionSkeleton } from "./cortex/SectionSkeleton";
import { DeployInfoFooter } from "./operator/DeployInfoFooter";
import { OperatorConnectorsTable } from "./operator/OperatorConnectorsTable";
import { useOperatorOverview } from "./operator/useOperatorOverview";

export default function AdminCortexIngestionPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "runs" ? "runs" : "connectors";
  const overviewQ = useOperatorOverview();

  const setTab = (next: "connectors" | "runs") => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "runs") params.set("tab", "runs");
      else params.delete("tab");
      params.delete("page");
      return params;
    });
  };

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Ingestion</h1>
        <p className="mt-1 text-sm text-stone-600">
          Connector sync and raw ingestion history. Pipeline actions live on{" "}
          <Link
            to={`/admin/tenants/${tenantId}/cortex/overview`}
            className="font-medium text-indigo-700 no-underline hover:underline"
          >
            Overview
          </Link>
          .
        </p>
      </header>

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
          <OperatorConnectorsTable connectors={overviewQ.data?.connectors ?? []} />
        )
      ) : (
        <IngestionRunsTab />
      )}

      <DeployInfoFooter />
    </div>
  );
}
