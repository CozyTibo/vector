import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE } from "./adminConstants";
import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { CortexOverview, formatRelativeAge, titleConnector } from "./cortexAdminTypes";
import AdminFeedbackBanner from "./ui/AdminFeedbackBanner";
import { StatusBadge } from "./ui/StatusBadge";

type TriggerSyncResponse = {
  enqueued?: boolean;
  queue?: string;
  connector: string;
  sync_mode?: string;
};

type SyncFeedback = { kind: "success" | "error"; message: string };

function ConnectorsSummary({ connectors }: { connectors: CortexOverview["connectors"] }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [feedback, setFeedback] = useState<SyncFeedback | null>(null);
  const [pendingConnector, setPendingConnector] = useState<string | null>(null);

  const syncMut = useMutation({
    mutationFn: async (connector: string) => {
      setPendingConnector(connector);
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ connector, confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return (await res.json()) as TriggerSyncResponse;
    },
    onSuccess: (data) => {
      const label = titleConnector(data.connector);
      setFeedback({
        kind: "success",
        message: `${label} sync queued on ${data.queue ?? "cortex_live"} (${data.sync_mode ?? "incremental"}). Waiting for the worker to finish…`,
      });
      const poll = async (attempt: number) => {
        await qc.refetchQueries({ queryKey: ["admin-cortex-phase-summary", tenantId, "ingestion"] });
        void qc.invalidateQueries({ queryKey: ["admin-cortex-pipeline-overview", tenantId] });
        const summary = qc.getQueryData<
          PhaseSummaryPayload & { connectors?: CortexOverview["connectors"] }
        >(["admin-cortex-phase-summary", tenantId, "ingestion"]);
        const row = summary?.connectors?.find((c) => c.connector === data.connector);
        const latest = row?.latest_run;
        const runIsFresh =
          latest?.started_at != null &&
          Date.now() - new Date(latest.started_at).getTime() < 5 * 60_000;
        if (latest && attempt > 0 && runIsFresh) {
          const rows =
            latest.raw_rows_written != null ? latest.raw_rows_written.toLocaleString() : "0";
          const age = formatRelativeAge(latest.started_at);
          const rowsNote =
            latest.raw_rows_written === 0
              ? " No new raw rows this run — incremental may be caught up, or check Slack channel selection and API rate limits."
              : "";
          setFeedback({
            kind: "success",
            message: `${label} sync finished: ${latest.status} (${age}), ${rows} row(s) written.${rowsNote}`,
          });
          return;
        }
        if (attempt < 24) {
          window.setTimeout(() => void poll(attempt + 1), 5000);
        } else {
          setFeedback({
            kind: "error",
            message: `${label} was queued but no new run appeared after 2 minutes. Check the worker (cortex_live queue) and Overview → Recent ingestion runs.`,
          });
        }
      };
      void poll(0);
    },
    onError: (err: Error) => {
      setFeedback({
        kind: "error",
        message: err.message || "Failed to queue sync.",
      });
    },
    onSettled: () => {
      setPendingConnector(null);
    },
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">Connectors</h2>
      <p className="mt-1 text-xs text-stone-600">
        Sync now queues one manual job on the live worker queue. Success means enqueued, not finished.
      </p>
      {feedback ? (
        <div className="mt-3">
          <AdminFeedbackBanner
            kind={feedback.kind}
            message={feedback.message}
            onDismiss={() => setFeedback(null)}
          />
        </div>
      ) : null}
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className="bg-stone-50 text-left text-stone-700">
            <tr>
              <th className="px-2 py-2">connector</th>
              <th className="px-2 py-2">routed</th>
              <th className="px-2 py-2">connection</th>
              <th className="px-2 py-2">last sync</th>
              <th className="px-2 py-2 text-right">ingested rows</th>
              <th className="px-2 py-2 text-right">last run rows</th>
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
                  <td className="px-2 py-2 text-right font-medium tabular-nums text-stone-900">
                    {(row.ingested_row_count ?? 0).toLocaleString()}
                  </td>
                  <td className="px-2 py-2 text-right tabular-nums text-stone-600">
                    {latest?.raw_rows_written != null ? latest.raw_rows_written.toLocaleString() : "—"}
                  </td>
                  <td className="px-2 py-2">
                    <button
                      type="button"
                      className="rounded border border-indigo-300 bg-indigo-50 px-2 py-1 text-[11px] disabled:opacity-40"
                      disabled={!canAct || syncMut.isPending}
                      onClick={() => {
                        setFeedback(null);
                        syncMut.mutate(row.connector);
                      }}
                    >
                      {pendingConnector === row.connector ? "Queueing…" : "sync now"}
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
