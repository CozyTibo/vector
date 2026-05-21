import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CortexRecentRuns } from "../cortexAdminTypes";
import { apiRunToTableRow, IngestionRunsTable } from "./IngestionRunsTable";

const PAGE_SIZE = 50;

const CONNECTOR_FILTERS = [
  { value: "", label: "All connectors" },
  { value: "slack", label: "Slack" },
  { value: "notion", label: "Notion" },
  { value: "github", label: "GitHub" },
  { value: "linear", label: "Linear" },
  { value: "google_drive", label: "Google Drive" },
  { value: "calls", label: "Calls" },
];

export function IngestionRunsTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const connectorFilter = searchParams.get("connector") ?? "";
  const page = Math.max(0, Number.parseInt(searchParams.get("page") ?? "0", 10) || 0);
  const offset = page * PAGE_SIZE;

  const runsQ = useQuery({
    queryKey: ["admin-cortex-ingestion-runs", tenantId, connectorFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      if (connectorFilter) params.set("connector", connectorFilter);
      return adminJson<CortexRecentRuns & { total_count: number; offset: number; limit: number }>(
        `/admin/tenants/${tenantId}/cortex/ingestion/recent-runs?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const data = runsQ.data;
  const total = data?.total_count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  const setConnector = (connector: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", "runs");
      if (connector) next.set("connector", connector);
      else next.delete("connector");
      next.delete("page");
      return next;
    });
  };

  const setPage = (nextPage: number) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", "runs");
      if (nextPage <= 0) next.delete("page");
      else next.set("page", String(nextPage));
      return next;
    });
  };

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-stone-900">Ingestion runs</h2>
          <p className="text-sm text-stone-600">
            Full connector sync history · newest first
          </p>
        </div>
        <label className="text-xs text-stone-600">
          Filter
          <select
            className="ml-2 rounded border border-stone-300 bg-white px-2 py-1 text-xs"
            value={connectorFilter}
            onChange={(e) => setConnector(e.target.value)}
          >
            {CONNECTOR_FILTERS.map((opt) => (
              <option key={opt.value || "all"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {runsQ.isPending ? (
        <p className="mt-4 text-sm text-stone-500">Loading runs…</p>
      ) : runsQ.isError ? (
        <p className="mt-4 text-sm text-red-700">{(runsQ.error as Error).message}</p>
      ) : (
        <>
          <p className="mt-3 text-xs text-stone-500">
            {total === 0
              ? "No runs match this filter."
              : `Showing ${from.toLocaleString()}–${to.toLocaleString()} of ${total.toLocaleString()} run(s)`}
          </p>
          <div className="mt-3">
            <IngestionRunsTable
              runs={(data?.items ?? []).map(apiRunToTableRow)}
              showFinished
              showSyncMode
              showError
            />
          </div>
          {total > PAGE_SIZE ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
                disabled={page <= 0}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <span className="text-xs text-stone-600">
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
                disabled={page + 1 >= pageCount}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
