import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE } from "./adminConstants";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { CortexOverview, formatRelativeAge, titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

type ExplorerPayload = {
  items: Array<{
    connector: string;
    external_id: string;
    ingested_at: string;
    resource_type: string;
    payload_preview: string;
    evidence: Record<string, unknown>;
  }>;
  truncated: boolean;
  total: number;
  limit: number;
  offset: number;
};

function ConnectorsSummary({ connectors }: { connectors: CortexOverview["connectors"] }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const syncMut = useMutation({
    mutationFn: async (connector: string) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ connector, confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-phase-summary", tenantId, "ingestion"] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-pipeline-overview", tenantId] });
    },
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">Connectors</h2>
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className="bg-stone-50 text-left text-stone-700">
            <tr>
              <th className="px-2 py-2">connector</th>
              <th className="px-2 py-2">routed</th>
              <th className="px-2 py-2">connection</th>
              <th className="px-2 py-2">last sync</th>
              <th className="px-2 py-2">rows</th>
              <th className="px-2 py-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {connectors.map((row) => {
              const canAct = row.cortex_routed && row.connection_status === "active";
              const latest = row.latest_run;
              return (
                <tr key={row.connector} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-medium">{titleConnector(row.connector)}</td>
                  <td className="px-2 py-2">
                    <StatusBadge tone={row.cortex_routed ? "ok" : "neutral"}>
                      {row.cortex_routed ? "yes" : "no"}
                    </StatusBadge>
                  </td>
                  <td className="px-2 py-2">{row.connection_status ?? "not connected"}</td>
                  <td className="px-2 py-2">
                    {latest ? `${latest.status} (${formatRelativeAge(latest.started_at)})` : "n/a"}
                  </td>
                  <td className="px-2 py-2">{latest?.raw_rows_written ?? "n/a"}</td>
                  <td className="px-2 py-2">
                    <button
                      type="button"
                      className="rounded border border-indigo-300 bg-indigo-50 px-2 py-1 text-[11px] disabled:opacity-40"
                      disabled={!canAct || syncMut.isPending}
                      onClick={() => syncMut.mutate(row.connector)}
                    >
                      sync now
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function IngestionExplorer() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [connector, setConnector] = useState("slack");
  const [offset, setOffset] = useState(0);
  const [resourceType, setResourceType] = useState("");
  const [search, setSearch] = useState("");

  const explorerQ = useQuery({
    queryKey: ["admin-cortex-phase-explorer", tenantId, "ingestion", connector, offset, resourceType, search],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "50", offset: String(offset) });
      if (resourceType.trim()) params.set("resource_type", resourceType.trim());
      if (search.trim()) params.set("search_query", search.trim());
      params.set("connector", connector);
      return adminJson<ExplorerPayload>(
        `/admin/tenants/${tenantId}/cortex/pipeline/phases/ingestion/explorer?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  return (
    <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">Raw explorer</h2>
      <div className="flex flex-wrap gap-2 text-xs">
        <label>
          connector
          <input
            className="ml-1 rounded border border-stone-300 px-2 py-1"
            value={connector}
            onChange={(e) => {
              setConnector(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label>
          resource_type
          <input
            className="ml-1 rounded border border-stone-300 px-2 py-1"
            value={resourceType}
            onChange={(e) => {
              setResourceType(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label>
          search
          <input
            className="ml-1 rounded border border-stone-300 px-2 py-1"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </label>
      </div>
      <div className="overflow-x-auto rounded border border-stone-200">
        <table className="min-w-full text-xs">
          <thead className="bg-stone-50 text-left">
            <tr>
              <th className="px-2 py-1">connector</th>
              <th className="px-2 py-1">external_id</th>
              <th className="px-2 py-1">ingested_at</th>
              <th className="px-2 py-1">resource_type</th>
              <th className="px-2 py-1">preview</th>
            </tr>
          </thead>
          <tbody>
            {(explorerQ.data?.items ?? []).map((row, i) => (
              <Fragment key={`${row.external_id}-${i}`}>
                <tr className="border-t border-stone-100">
                  <td className="px-2 py-1">{titleConnector(row.connector)}</td>
                  <td className="px-2 py-1">{row.external_id}</td>
                  <td className="px-2 py-1">{new Date(row.ingested_at).toLocaleString()}</td>
                  <td className="px-2 py-1 font-mono">{row.resource_type}</td>
                  <td className="px-2 py-1 text-stone-600">{row.payload_preview || "—"}</td>
                </tr>
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-40"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - 50))}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-40"
          disabled={!explorerQ.data?.truncated}
          onClick={() => setOffset((o) => o + 50)}
        >
          Next
        </button>
      </div>
    </section>
  );
}

export default function AdminCortexIngestionPage() {
  return (
    <PhasePageShell
      phase="ingestion"
      title="Ingestion"
      description="Connector sync, checkpoints, and raw records. Full pipeline runs from Overview."
      summaryContent={(summary) => {
        const ext = summary as PhaseSummaryPayload & {
          connectors?: CortexOverview["connectors"];
          checkpoints?: Array<{ connector: string; checkpoint_last_incremental_at: string | null }>;
        };
        const connectors = ext.connectors ?? [];
        return (
          <>
            <ConnectorsSummary connectors={connectors} />
            {ext.checkpoints && ext.checkpoints.length > 0 ? (
              <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                <h2 className="text-base font-semibold text-stone-900">Checkpoints</h2>
                <table className="mt-3 min-w-full text-xs">
                  <thead className="bg-stone-50 text-left">
                    <tr>
                      <th className="px-2 py-1">connector</th>
                      <th className="px-2 py-1">incremental cursor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ext.checkpoints.map((row) => (
                      <tr key={row.connector} className="border-t border-stone-100">
                        <td className="px-2 py-1">{titleConnector(row.connector)}</td>
                        <td className="px-2 py-1 font-mono">{row.checkpoint_last_incremental_at ?? "n/a"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ) : null}
          </>
        );
      }}
      explorerContent={<IngestionExplorer />}
    />
  );
}
