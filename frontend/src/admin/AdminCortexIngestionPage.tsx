import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE, CORTEX_REPLAY_CONFIRM_PHRASE } from "./adminConstants";
import {
  CortexExhaustCoverage,
  CortexOverview,
  CortexRawRecords,
  CortexRawStats,
  CortexRecentRuns,
  CortexVerification,
  formatRelativeAge,
  titleConnector,
} from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

type IngestionTab =
  | "dashboard"
  | "connectors"
  | "checkpoints"
  | "replays"
  | "raw-explorer"
  | "verification"
  | "coverage"
  | "metrics";

const TAB_ORDER: IngestionTab[] = [
  "dashboard",
  "connectors",
  "checkpoints",
  "replays",
  "raw-explorer",
  "verification",
  "coverage",
  "metrics",
];

const TAB_LABEL: Record<IngestionTab, string> = {
  dashboard: "Dashboard",
  connectors: "Connectors",
  checkpoints: "Checkpoints",
  replays: "Replays",
  "raw-explorer": "Raw Explorer",
  verification: "Verification",
  coverage: "Coverage / Exhaust",
  metrics: "Metrics",
};

function tabCls(active: boolean): string {
  return [
    "rounded-md border px-3 py-1.5 text-sm font-medium",
    active
      ? "border-indigo-300 bg-indigo-100 text-indigo-900"
      : "border-stone-200 bg-white text-stone-700 hover:bg-stone-100",
  ].join(" ");
}

function parseTab(searchParams: URLSearchParams): IngestionTab {
  const raw = searchParams.get("tab");
  if (raw && TAB_ORDER.includes(raw as IngestionTab)) return raw as IngestionTab;
  return "dashboard";
}

type ActionResult = { connector: string; ok: boolean; detail?: string };

function ConnectorsTable({
  rows,
  onSyncOne,
  onReplayOne,
  onInspectRaw,
}: {
  rows: CortexOverview["connectors"];
  onSyncOne: (connector: string) => void;
  onReplayOne: (connector: string) => void;
  onInspectRaw: (connector: string) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
      <table className="min-w-full text-xs">
        <thead className="bg-stone-50 text-left text-stone-700">
          <tr>
            <th className="px-2 py-2">connector</th>
            <th className="px-2 py-2">routed</th>
            <th className="px-2 py-2">connection</th>
            <th className="px-2 py-2">last sync</th>
            <th className="px-2 py-2">duration</th>
            <th className="px-2 py-2">rows</th>
            <th className="px-2 py-2">failures</th>
            <th className="px-2 py-2">checkpoint freshness</th>
            <th className="px-2 py-2">replay support</th>
            <th className="px-2 py-2">actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const canAct = row.cortex_routed && row.connection_status === "active";
            const latest = row.latest_run;
            const duration =
              latest?.started_at && latest?.finished_at
                ? `${Math.max(0, Math.round((new Date(latest.finished_at).getTime() - new Date(latest.started_at).getTime()) / 1000))}s`
                : "n/a";
            const failed = latest?.status === "FAILED";
            const isExpanded = expanded === row.connector;
            return (
              <>
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
                  <td className="px-2 py-2">{duration}</td>
                  <td className="px-2 py-2">{latest?.raw_rows_written ?? "n/a"}</td>
                  <td className="px-2 py-2">{failed ? 1 : 0}</td>
                  <td className="px-2 py-2">{formatRelativeAge(row.checkpoint_last_incremental_at)}</td>
                  <td className="px-2 py-2">yes</td>
                  <td className="px-2 py-2">
                    <div className="flex flex-wrap gap-1">
                      <button
                        type="button"
                        className="rounded border border-indigo-300 bg-indigo-50 px-2 py-1 text-[11px] text-indigo-900 disabled:opacity-40"
                        disabled={!canAct}
                        onClick={() => onSyncOne(row.connector)}
                      >
                        ingest
                      </button>
                      <button
                        type="button"
                        className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] text-amber-900 disabled:opacity-40"
                        disabled={!canAct}
                        onClick={() => onReplayOne(row.connector)}
                      >
                        replay
                      </button>
                      <button
                        type="button"
                        className="rounded border border-stone-300 bg-white px-2 py-1 text-[11px] text-stone-800"
                        onClick={() => onInspectRaw(row.connector)}
                      >
                        inspect raw
                      </button>
                      <button
                        type="button"
                        className="rounded border border-stone-300 bg-white px-2 py-1 text-[11px] text-stone-800"
                        onClick={() => setExpanded(isExpanded ? null : row.connector)}
                      >
                        {isExpanded ? "collapse" : "expand"}
                      </button>
                    </div>
                  </td>
                </tr>
                {isExpanded ? (
                  <tr className="border-t border-stone-100 bg-stone-50/50">
                    <td className="px-3 py-3 text-[11px] text-stone-700" colSpan={10}>
                      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                        <div>
                          <p className="font-semibold text-stone-900">Latest run</p>
                          <p>status: {latest?.status ?? "n/a"}</p>
                          <p>trigger: {latest?.source_trigger ?? "n/a"}</p>
                          <p>run id: {latest?.run_id ?? "n/a"}</p>
                        </div>
                        <div>
                          <p className="font-semibold text-stone-900">Checkpoint</p>
                          <p>last incremental: {row.checkpoint_last_incremental_at ?? "n/a"}</p>
                          <p>scope: default (structured explorer in Checkpoints tab)</p>
                        </div>
                        <div>
                          <p className="font-semibold text-stone-900">Warnings</p>
                          <p>{!row.cortex_routed ? "Not routed to Cortex." : "Routed."}</p>
                          <p>{row.connection_status !== "active" ? "Inactive connection." : "Connection active."}</p>
                          <p>{failed ? latest?.error_summary ?? "Run failed." : "No recent failure."}</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : null}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminCortexIngestionPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = parseTab(searchParams);
  const qc = useQueryClient();

  const [selectedConnector, setSelectedConnector] = useState<string>("slack");
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [rawOffset, setRawOffset] = useState(0);
  const [rawResourceType, setRawResourceType] = useState("");
  const [rawSearch, setRawSearch] = useState("");
  const [rawIncludeHealth, setRawIncludeHealth] = useState(false);
  const [expandedRawId, setExpandedRawId] = useState<number | null>(null);

  const overviewQ = useQuery({
    queryKey: ["admin-cortex-overview", tenantId],
    queryFn: () => adminJson<CortexOverview>(`/admin/tenants/${tenantId}/cortex/ingestion`),
    enabled: Boolean(tenantId),
  });
  const coverageQ = useQuery({
    queryKey: ["admin-cortex-exhaust-coverage", tenantId],
    queryFn: () =>
      adminJson<CortexExhaustCoverage>(`/admin/tenants/${tenantId}/cortex/ingestion/exhaust-coverage`),
    enabled: Boolean(tenantId),
  });
  const statsQ = useQuery({
    queryKey: ["admin-cortex-raw-stats", tenantId],
    queryFn: () => adminJson<CortexRawStats>(`/admin/tenants/${tenantId}/cortex/ingestion/raw-stats`),
    enabled: Boolean(tenantId),
  });
  const recentRunsQ = useQuery({
    queryKey: ["admin-cortex-recent-runs", tenantId],
    queryFn: () => adminJson<CortexRecentRuns>(`/admin/tenants/${tenantId}/cortex/ingestion/recent-runs?limit=50`),
    enabled: Boolean(tenantId),
  });

  const rawQ = useQuery({
    queryKey: [
      "admin-cortex-connector-raw",
      tenantId,
      selectedConnector,
      rawOffset,
      rawResourceType,
      rawSearch,
      rawIncludeHealth,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: "50",
        offset: String(rawOffset),
      });
      if (rawResourceType.trim()) params.set("resource_type", rawResourceType.trim());
      if (rawSearch.trim()) params.set("search_query", rawSearch.trim());
      if (rawIncludeHealth) params.set("include_health_rows", "true");
      return adminJson<CortexRawRecords>(
        `/admin/tenants/${tenantId}/cortex/ingestion/connectors/${selectedConnector}/raw-records?${params}`,
      );
    },
    enabled: Boolean(tenantId && selectedConnector),
  });

  const verifyMut = useMutation({
    mutationFn: () => adminJson<CortexVerification>(`/admin/tenants/${tenantId}/cortex/ingestion/verification`),
  });

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
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
    },
  });

  const replayMut = useMutation({
    mutationFn: async (connector: string) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-replay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          connector,
          replay_version: 1,
          confirmation: CORTEX_REPLAY_CONFIRM_PHRASE,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
    },
  });

  const bulkReplayMut = useMutation({
    mutationFn: async (connectors: string[]) => {
      const results = await Promise.all(
        connectors.map(async (connector): Promise<ActionResult> => {
          try {
            const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-replay`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                connector,
                replay_version: 1,
                confirmation: CORTEX_REPLAY_CONFIRM_PHRASE,
              }),
            });
            if (!res.ok) return { connector, ok: false, detail: await readErrorDetail(res) };
            return { connector, ok: true };
          } catch (e) {
            return { connector, ok: false, detail: (e as Error).message };
          }
        }),
      );
      return results;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
    },
  });

  const bulkSyncMut = useMutation({
    mutationFn: async (connectors: string[]) => {
      const results = await Promise.all(
        connectors.map(async (connector): Promise<ActionResult> => {
          try {
            const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ connector, confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE }),
            });
            if (!res.ok) return { connector, ok: false, detail: await readErrorDetail(res) };
            return { connector, ok: true };
          } catch (e) {
            return { connector, ok: false, detail: (e as Error).message };
          }
        }),
      );
      return results;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
    },
  });

  const metrics = useMemo(() => {
    const resources = statsQ.data?.resources ?? [];
    const totalRows = resources.reduce((sum, row) => sum + row.row_count, 0);
    const largest = [...resources].sort((a, b) => b.row_count - a.row_count).slice(0, 5);
    const replayRows = rawQ.data?.items.filter((x) => Boolean(x.replay_job_id)).length ?? 0;
    return { totalRows, largest, replayRows };
  }, [statsQ.data, rawQ.data]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (overviewQ.isPending) return <p className="text-sm text-stone-600">Loading ingestion control plane…</p>;
  if (overviewQ.isError) return <p className="text-sm text-red-700">{(overviewQ.error as Error).message}</p>;
  const o = overviewQ.data;
  const runnableConnectors = o.connectors
    .filter((x) => x.cortex_routed && x.connection_status === "active")
    .map((x) => x.connector);
  const selectedReplayTargets = selectedRows.length > 0 ? selectedRows : runnableConnectors;
  const recentRuns = recentRunsQ.data?.items ?? [];
  const replayRuns = recentRuns.filter((x) => x.replay_mode);
  const replayTableRows = replayRuns.length > 0 ? replayRuns : recentRuns.slice(0, 20);
  const replayFallbackToLive = replayRuns.length === 0;

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Ingestion Operations</h2>
            <p className="text-sm text-stone-600">Queue throughput, connector controls, replay, checkpoints, and raw explorer.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {TAB_ORDER.map((tab) => (
              <button
                key={tab}
                type="button"
                className={tabCls(activeTab === tab)}
                onClick={() => setSearchParams({ tab })}
              >
                {TAB_LABEL[tab]}
              </button>
            ))}
          </div>
        </div>
      </section>

      {activeTab === "dashboard" ? (
        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-stone-500">Ingestion rate</p>
            <p className="mt-1 text-lg font-semibold text-stone-900">{metrics.totalRows}</p>
            <p className="text-xs text-stone-600">Total observed rows</p>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-stone-500">Replay activity</p>
            <p className="mt-1 text-lg font-semibold text-stone-900">
              {recentRunsQ.data?.items.filter((x) => x.replay_mode).length ?? 0}
            </p>
            <p className="text-xs text-stone-600">Recent replay runs (limit 50)</p>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-stone-500">Failures</p>
            <p className="mt-1 text-lg font-semibold text-stone-900">
              {recentRunsQ.data?.items.filter((x) => x.status === "FAILED").length ?? 0}
            </p>
            <p className="text-xs text-stone-600">Failed runs in recent history</p>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-stone-500">Dedupe</p>
            <p className="mt-1 text-lg font-semibold text-stone-900">Pending metric</p>
            <p className="text-xs text-stone-600">Conflict-noop ratio endpoint pending</p>
          </div>
        </section>
      ) : null}

      {activeTab === "connectors" ? (
        <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-stone-700">Table-first connector operations with row expansion for diagnostics.</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-900 disabled:opacity-40"
                disabled={bulkSyncMut.isPending || runnableConnectors.length === 0}
                onClick={() => bulkSyncMut.mutate(runnableConnectors)}
              >
                {bulkSyncMut.isPending ? "Queueing…" : "Ingest all connectors"}
              </button>
              <button
                type="button"
                className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900 disabled:opacity-40"
                disabled={bulkReplayMut.isPending || selectedReplayTargets.length === 0}
                onClick={() => bulkReplayMut.mutate(selectedReplayTargets)}
              >
                {bulkReplayMut.isPending ? "Queueing…" : "Replay selected"}
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {o.connectors.map((row) => {
              const checked = selectedRows.includes(row.connector);
              return (
                <label key={row.connector} className="inline-flex items-center gap-2 text-xs text-stone-700">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      setSelectedRows((prev) =>
                        e.target.checked ? [...new Set([...prev, row.connector])] : prev.filter((x) => x !== row.connector),
                      );
                    }}
                  />
                  {titleConnector(row.connector)}
                </label>
              );
            })}
          </div>

          <ConnectorsTable
            rows={o.connectors}
            onSyncOne={(connector) => syncMut.mutate(connector)}
            onReplayOne={(connector) => replayMut.mutate(connector)}
            onInspectRaw={(connector) => {
              setSelectedConnector(connector);
              setSearchParams({ tab: "raw-explorer" });
            }}
          />
        </section>
      ) : null}

      {activeTab === "checkpoints" ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Checkpoint Explorer</h3>
          <p className="mt-1 text-sm text-stone-600">
            Structured scope/tree endpoint is pending; current checkpoint freshness is shown per connector.
          </p>
          <div className="mt-3 overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-1">connector</th>
                  <th className="px-2 py-1">incremental cursor</th>
                  <th className="px-2 py-1">lag</th>
                  <th className="px-2 py-1">warning</th>
                </tr>
              </thead>
              <tbody>
                {o.connectors.map((row) => (
                  <tr key={row.connector} className="border-t border-stone-100">
                    <td className="px-2 py-1">{titleConnector(row.connector)}</td>
                    <td className="px-2 py-1 font-mono">{row.checkpoint_last_incremental_at ?? "n/a"}</td>
                    <td className="px-2 py-1">{formatRelativeAge(row.checkpoint_last_incremental_at)}</td>
                    <td className="px-2 py-1">
                      {row.checkpoint_last_incremental_at ? "none" : "stale or missing checkpoint"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {activeTab === "replays" ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Replay Operations</h3>
          <p className="mt-1 text-sm text-stone-600">
            Replay history by recent runs; job-centric endpoint pending.
            {replayFallbackToLive
              ? " No replay runs yet, so recent live runs are shown for visibility."
              : ""}
          </p>
          <div className="mt-3 overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-1">started</th>
                  <th className="px-2 py-1">connector</th>
                  <th className="px-2 py-1">lane</th>
                  <th className="px-2 py-1">status</th>
                  <th className="px-2 py-1">replay job</th>
                  <th className="px-2 py-1">version</th>
                  <th className="px-2 py-1">rows</th>
                </tr>
              </thead>
              <tbody>
                {replayTableRows.map((run) => (
                    <tr key={run.run_id} className="border-t border-stone-100">
                      <td className="px-2 py-1">{new Date(run.started_at).toLocaleString()}</td>
                      <td className="px-2 py-1">{titleConnector(run.connector)}</td>
                      <td className="px-2 py-1">{run.replay_mode ? "replay" : "live"}</td>
                      <td className="px-2 py-1">{run.status}</td>
                      <td className="px-2 py-1 font-mono">{run.replay_job_id ?? "n/a"}</td>
                      <td className="px-2 py-1">{run.replay_version ?? "n/a"}</td>
                      <td className="px-2 py-1">{run.raw_rows_written ?? "n/a"}</td>
                    </tr>
                  ))}
                {replayTableRows.length === 0 ? (
                  <tr className="border-t border-stone-100">
                    <td className="px-2 py-2 text-stone-500" colSpan={7}>
                      No runs found yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {activeTab === "raw-explorer" ? (
        <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Raw Explorer</h3>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs text-stone-600">
              connector
              <select
                value={selectedConnector}
                className="ml-2 rounded border border-stone-300 px-2 py-1 text-xs"
                onChange={(e) => {
                  setSelectedConnector(e.target.value);
                  setRawOffset(0);
                }}
              >
                {o.connectors.map((row) => (
                  <option key={row.connector} value={row.connector}>
                    {titleConnector(row.connector)}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-stone-600">
              resource_type
              <input
                value={rawResourceType}
                onChange={(e) => {
                  setRawResourceType(e.target.value);
                  setRawOffset(0);
                }}
                className="ml-2 rounded border border-stone-300 px-2 py-1 text-xs"
              />
            </label>
            <label className="text-xs text-stone-600">
              search
              <input
                value={rawSearch}
                onChange={(e) => {
                  setRawSearch(e.target.value);
                  setRawOffset(0);
                }}
                className="ml-2 rounded border border-stone-300 px-2 py-1 text-xs"
              />
            </label>
            <label className="inline-flex items-center gap-2 text-xs text-stone-700">
              <input
                type="checkbox"
                checked={rawIncludeHealth}
                onChange={(e) => {
                  setRawIncludeHealth(e.target.checked);
                  setRawOffset(0);
                }}
              />
              include health rows
            </label>
          </div>
          <div className="overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-1 w-24">payload</th>
                  <th className="px-2 py-1">fetched_at</th>
                  <th className="px-2 py-1">resource_type</th>
                  <th className="px-2 py-1">external_id</th>
                  <th className="px-2 py-1">source_identity_key</th>
                  <th className="px-2 py-1">source_revision_key</th>
                  <th className="px-2 py-1">lane</th>
                  <th className="px-2 py-1">http</th>
                </tr>
              </thead>
              <tbody>
                {(rawQ.data?.items ?? []).map((row) => {
                  const expanded = expandedRawId === row.id;
                  const qpKeys = Object.keys(row.query_params ?? {});
                  const payloadKeys = Object.keys(row.payload_body ?? {});
                  return (
                    <Fragment key={row.id}>
                      <tr className="border-t border-stone-100">
                        <td className="px-2 py-1 align-top">
                          <button
                            type="button"
                            className="rounded border border-stone-300 bg-white px-2 py-0.5 text-[11px] text-stone-800 hover:bg-stone-50"
                            onClick={() => setExpandedRawId(expanded ? null : row.id)}
                          >
                            {expanded ? "hide" : "show"}
                          </button>
                        </td>
                        <td className="px-2 py-1">{new Date(row.fetched_at).toLocaleString()}</td>
                        <td className="px-2 py-1 font-mono">{row.resource_type}</td>
                        <td className="px-2 py-1">{row.external_id}</td>
                        <td className="px-2 py-1 font-mono">{row.source_identity_key ?? "n/a"}</td>
                        <td className="px-2 py-1 font-mono">{row.source_revision_key ?? "n/a"}</td>
                        <td className="px-2 py-1">{row.replay_job_id ? "replay" : "live"}</td>
                        <td className="px-2 py-1">{row.http_status}</td>
                      </tr>
                      {expanded ? (
                        <tr className="border-t border-stone-100 bg-stone-50/80">
                          <td className="px-2 py-2 align-top text-stone-700" colSpan={8}>
                            <div className="space-y-2 text-[11px]">
                              {row.api_endpoint ? (
                                <p>
                                  <span className="font-semibold text-stone-900">api_endpoint</span>{" "}
                                  <span className="break-all font-mono">{row.api_endpoint}</span>
                                </p>
                              ) : null}
                              {qpKeys.length > 0 ? (
                                <div>
                                  <p className="font-semibold text-stone-900">query_params</p>
                                  <pre className="mt-1 max-h-40 overflow-auto rounded border border-stone-200 bg-white p-2 font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-all">
                                    {JSON.stringify(row.query_params, null, 2)}
                                  </pre>
                                </div>
                              ) : null}
                              <div>
                                <p className="font-semibold text-stone-900">
                                  payload_body{" "}
                                  <span className="font-normal text-stone-500">
                                    ({payloadKeys.length} top-level key{payloadKeys.length === 1 ? "" : "s"})
                                  </span>
                                </p>
                                <pre className="mt-1 max-h-96 overflow-auto rounded border border-stone-200 bg-white p-2 font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-all">
                                  {JSON.stringify(row.payload_body ?? {}, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded border border-stone-300 bg-white px-2 py-1 text-xs disabled:opacity-40"
              disabled={rawOffset === 0}
              onClick={() => setRawOffset((prev) => Math.max(0, prev - 50))}
            >
              Previous
            </button>
            <button
              type="button"
              className="rounded border border-stone-300 bg-white px-2 py-1 text-xs disabled:opacity-40"
              disabled={!rawQ.data?.truncated}
              onClick={() => setRawOffset((prev) => prev + 50)}
            >
              Next
            </button>
          </div>
        </section>
      ) : null}

      {activeTab === "verification" ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded border border-stone-300 bg-white px-3 py-2 text-sm"
              disabled={verifyMut.isPending}
              onClick={() => verifyMut.mutate()}
            >
              {verifyMut.isPending ? "Running…" : "Run verification"}
            </button>
            {verifyMut.data ? (
              <StatusBadge tone={verifyMut.data.passed ? "ok" : "bad"}>
                {verifyMut.data.passed ? "passed" : "failed"}
              </StatusBadge>
            ) : null}
          </div>
          {verifyMut.data?.exhaust_depth?.gate_checks ? (
            <ul className="mt-3 space-y-1 text-sm text-stone-700">
              {verifyMut.data.exhaust_depth.gate_checks.map((check) => (
                <li key={check.id}>
                  {check.id}: {check.passed ? "ok" : "fail"}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {activeTab === "coverage" ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Coverage / Exhaust</h3>
          <div className="mt-3 overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-1">connector</th>
                  <th className="px-2 py-1">maturity</th>
                  <th className="px-2 py-1">missing streams</th>
                  <th className="px-2 py-1">replay support</th>
                </tr>
              </thead>
              <tbody>
                {(coverageQ.data?.connectors ?? []).map((row) => (
                  <tr key={row.connector} className="border-t border-stone-100">
                    <td className="px-2 py-1">{titleConnector(row.connector)}</td>
                    <td className="px-2 py-1">
                      L{row.maturity_level} - {row.maturity_level_title}
                    </td>
                    <td className="px-2 py-1">{row.missing_resource_types.join(", ") || "none"}</td>
                    <td className="px-2 py-1">{row.replay_compatibility_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {activeTab === "metrics" ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Metrics</h3>
          <p className="mt-1 text-sm text-stone-600">
            Live metrics endpoint is pending; this panel currently derives top stream volumes from raw stats.
          </p>
          <div className="mt-3 overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-1">connector</th>
                  <th className="px-2 py-1">resource_type</th>
                  <th className="px-2 py-1">rows</th>
                </tr>
              </thead>
              <tbody>
                {metrics.largest.map((row) => (
                  <tr key={`${row.connector}:${row.resource_type}`} className="border-t border-stone-100">
                    <td className="px-2 py-1">{titleConnector(row.connector)}</td>
                    <td className="px-2 py-1 font-mono">{row.resource_type}</td>
                    <td className="px-2 py-1">{row.row_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}
