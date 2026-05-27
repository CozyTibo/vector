import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { readErrorDetail } from "../../lib/canonicalApi";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE } from "../adminConstants";
import { titleConnector } from "../cortexAdminTypes";
import type { CortexCheckpointStreamSummary, CortexIngestionConnectorRow } from "../cortexAdminTypes";
import { SectionSkeleton } from "./SectionSkeleton";
import { invalidateCortexIngestionOverview } from "./useCortexIngestionOverview";

function syncAge(row: CortexIngestionConnectorRow): string {
  const latest = row.latest_run;
  const ts = (latest?.finished_at ?? latest?.started_at ?? row.checkpoint_last_incremental_at) as
    | string
    | undefined;
  if (!ts) return "never";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  const hours = (Date.now() - d.getTime()) / 3_600_000;
  if (hours < 1) return "<1h ago";
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function statusLabel(row: CortexIngestionConnectorRow): string {
  const latest = row.latest_run;
  if (!row.connection_id) return "not connected";
  if (row.connection_status !== "active") return row.connection_status ?? "inactive";
  if (!row.cortex_routed) return "not routed";
  return (latest?.status ?? "idle").toLowerCase();
}

function StreamCheckpointTable({ streams }: { streams: CortexCheckpointStreamSummary[] }) {
  if (streams.length === 0) {
    return <p className="text-xs text-stone-500">No checkpoint streams recorded yet.</p>;
  }
  return (
    <table className="mt-2 min-w-full text-xs">
      <thead>
        <tr className="border-b border-stone-200 text-left text-stone-500">
          <th className="py-1 pr-3 font-medium">Stream</th>
          <th className="py-1 pr-3 font-medium">Backfill</th>
          <th className="py-1 pr-3 font-medium">Introduced</th>
          <th className="py-1 pr-3 font-medium">Rows (last run)</th>
          <th className="py-1 font-medium">Cursor</th>
        </tr>
      </thead>
      <tbody>
        {streams.map((s) => (
          <tr key={s.stream_key} className="border-b border-stone-100">
            <td className="py-1 pr-3 font-mono text-stone-800">{s.stream_key}</td>
            <td className="py-1 pr-3 text-stone-600">{s.backfill_complete ? "yes" : "no"}</td>
            <td className="py-1 pr-3 text-stone-600">{s.introduced_at?.slice(0, 10) ?? "—"}</td>
            <td className="py-1 pr-3 text-stone-600">{s.rows_seen_last_run ?? "—"}</td>
            <td className="py-1 max-w-[8rem] truncate font-mono text-stone-500" title={s.next_cursor ?? ""}>
              {s.next_cursor ? `${s.next_cursor.slice(0, 12)}…` : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RawStatsSummary({ row }: { row: CortexIngestionConnectorRow }) {
  const stats = row.raw_resource_stats ?? [];
  if (stats.length === 0) return null;
  const top = [...stats].sort((a, b) => b.row_count - a.row_count).slice(0, 6);
  return (
    <p className="mt-2 text-xs text-stone-600">
      Raw store:{" "}
      {top.map((s) => `${s.resource_type} (${s.row_count.toLocaleString()})`).join(" · ")}
      {stats.length > top.length ? ` · +${stats.length - top.length} more` : ""}
    </p>
  );
}

type Props = {
  connectors: CortexIngestionConnectorRow[];
  loading?: boolean;
};

export function IngestionConnectorsTable({ connectors, loading }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const syncMut = useMutation({
    mutationFn: async (connector: string) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          connector,
          confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => invalidateCortexIngestionOverview(qc, tenantId),
  });

  const toggle = (connector: string) => {
    setExpanded((prev) => ({ ...prev, [connector]: !prev[connector] }));
  };

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Connectors</h2>
      <p className="mt-1 text-xs text-stone-500">
        Expand a row for checkpoint streams and raw counts by resource type.
      </p>
      {loading ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-xs uppercase tracking-wide text-stone-500">
                <th className="py-2 pr-4 w-8" />
                <th className="py-2 pr-4">Connector</th>
                <th className="py-2 pr-4">Last sync</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Raw rows</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {connectors.map((row) => {
                const isOpen = Boolean(expanded[row.connector]);
                const streams = row.checkpoint_streams ?? [];
                return (
                  <Fragment key={row.connector}>
                    <tr className="border-b border-stone-100">
                      <td className="py-2 pr-2">
                        <button
                          type="button"
                          className="text-stone-500 hover:text-stone-800"
                          aria-expanded={isOpen}
                          onClick={() => toggle(row.connector)}
                          disabled={!row.connection_id}
                        >
                          {isOpen ? "▼" : "▶"}
                        </button>
                      </td>
                      <td className="py-2 pr-4 font-medium text-stone-900">
                        {titleConnector(row.connector)}
                      </td>
                      <td className="py-2 pr-4 text-stone-600">{syncAge(row)}</td>
                      <td className="py-2 pr-4 text-stone-600">{statusLabel(row)}</td>
                      <td className="py-2 pr-4 tabular-nums text-stone-600">
                        {row.ingested_row_count.toLocaleString()}
                      </td>
                      <td className="py-2">
                        <button
                          type="button"
                          className="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                          disabled={
                            !row.connection_id ||
                            !row.cortex_routed ||
                            syncMut.isPending ||
                            syncMut.variables === row.connector
                          }
                          onClick={() => syncMut.mutate(row.connector)}
                        >
                          {syncMut.variables === row.connector && syncMut.isPending
                            ? "Enqueueing…"
                            : "Sync now"}
                        </button>
                      </td>
                    </tr>
                    {isOpen ? (
                      <tr className="border-b border-stone-100 bg-stone-50/80">
                        <td colSpan={6} className="px-4 py-3">
                          {row.checkpoint_exhaust_depth ? (
                            <p className="text-xs text-stone-600">
                              Exhaust depth:{" "}
                              <span className="font-medium">{row.checkpoint_exhaust_depth}</span>
                            </p>
                          ) : null}
                          <StreamCheckpointTable streams={streams} />
                          <RawStatsSummary row={row} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {syncMut.isError ? (
        <p className="mt-2 text-sm text-red-700">{(syncMut.error as Error).message}</p>
      ) : null}
    </section>
  );
}
