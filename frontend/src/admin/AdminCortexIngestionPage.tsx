import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE } from "./adminConstants";
import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { CortexOverview, formatRelativeAge, titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

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

export default function AdminCortexIngestionPage() {
  const [connector, setConnector] = useState("slack");

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
        return (
          <>
            <ConnectorsSummary connectors={ext.connectors ?? []} />
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
      explorerContent={
        <div className="space-y-3">
          <label className="text-xs text-stone-600">
            connector
            <input
              className="ml-2 rounded border border-stone-300 px-2 py-1 text-xs"
              value={connector}
              onChange={(e) => setConnector(e.target.value)}
            />
          </label>
          <PhaseExplorer phase="ingestion" connector={connector} />
        </div>
      }
    />
  );
}
