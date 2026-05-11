import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import {
  CORTEX_FLUSH_RERUN_CONFIRM_PHRASE,
  CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
  CORTEX_REPLAY_CONFIRM_PHRASE,
  CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE,
  CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE,
} from "./adminConstants";
import { CortexOverview, CortexRawStats, CortexRecentRuns, titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

type ActionResult = { connector: string; ok: boolean; detail?: string };
type ActionSummary = {
  kind: "sync" | "replay";
  okCount: number;
  failCount: number;
  okConnectors: string[];
  failures: ActionResult[];
};
type FlushRerunSummary = {
  enqueued_connectors: string[];
  canonical_backlog_task_id: string | null;
  deleted_rows_total: number;
};

function statCard(title: string, value: string, tone: "ok" | "warn" | "bad" | "neutral", detail?: string) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">{title}</p>
        <StatusBadge tone={tone}>{value}</StatusBadge>
      </div>
      {detail ? <p className="mt-2 text-xs text-stone-600">{detail}</p> : null}
    </div>
  );
}

export default function AdminCortexOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [lastActionSummary, setLastActionSummary] = useState<ActionSummary | null>(null);
  const [lastFlushRerunSummary, setLastFlushRerunSummary] = useState<FlushRerunSummary | null>(null);

  const refreshOverviewPulse = () => {
    const delays = [0, 1200, 3000, 6000, 10000, 14000];
    for (const ms of delays) {
      window.setTimeout(() => {
        void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
        void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
        void qc.invalidateQueries({ queryKey: ["admin-cortex-raw-stats", tenantId] });
      }, ms);
    }
  };

  const overviewQ = useQuery({
    queryKey: ["admin-cortex-overview", tenantId],
    queryFn: () => adminJson<CortexOverview>(`/admin/tenants/${tenantId}/cortex/ingestion`),
    enabled: Boolean(tenantId),
  });
  const rawStatsQ = useQuery({
    queryKey: ["admin-cortex-raw-stats", tenantId],
    queryFn: () => adminJson<CortexRawStats>(`/admin/tenants/${tenantId}/cortex/ingestion/raw-stats`),
    enabled: Boolean(tenantId),
  });
  const recentRunsQ = useQuery({
    queryKey: ["admin-cortex-recent-runs", tenantId],
    queryFn: () => adminJson<CortexRecentRuns>(`/admin/tenants/${tenantId}/cortex/ingestion/recent-runs?limit=25`),
    enabled: Boolean(tenantId),
  });

  const pauseMut = useMutation({
    mutationFn: async (paused: boolean) => {
      const res = await adminFetch("/admin/cortex/ingestion/scheduler-pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paused,
          confirmation: paused ? CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE : CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json() as Promise<{ paused_via_redis: boolean }>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
    },
  });

  const bulkSyncMut = useMutation({
    mutationFn: async (connectors: string[]): Promise<ActionResult[]> => {
      const results = await Promise.all(
        connectors.map(async (connector): Promise<ActionResult> => {
          const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ connector, confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE }),
          });
          if (!res.ok) return { connector, ok: false, detail: await readErrorDetail(res) };
          return { connector, ok: true };
        }),
      );
      return results;
    },
    onSuccess: (results) => {
      const failures = results.filter((x) => !x.ok);
      const okConnectors = results.filter((x) => x.ok).map((x) => x.connector);
      setLastActionSummary({
        kind: "sync",
        okCount: okConnectors.length,
        failCount: failures.length,
        okConnectors,
        failures,
      });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
      refreshOverviewPulse();
    },
  });

  const bulkReplayMut = useMutation({
    mutationFn: async (connectors: string[]): Promise<ActionResult[]> => {
      const results = await Promise.all(
        connectors.map(async (connector): Promise<ActionResult> => {
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
        }),
      );
      return results;
    },
    onSuccess: (results) => {
      const failures = results.filter((x) => !x.ok);
      const okConnectors = results.filter((x) => x.ok).map((x) => x.connector);
      setLastActionSummary({
        kind: "replay",
        okCount: okConnectors.length,
        failCount: failures.length,
        okConnectors,
        failures,
      });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
      refreshOverviewPulse();
    },
  });
  const flushRerunMut = useMutation({
    mutationFn: async (confirmation: string) => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/ingestion/actions/flush-rerun-to-identity`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            confirmation,
            canonical_batch_limit: 1000,
          }),
        },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json() as Promise<{
        enqueued_connectors: string[];
        canonical_backlog_task_id: string | null;
        deleted_rows_total: number;
      }>;
    },
    onSuccess: (payload) => {
      setLastFlushRerunSummary({
        enqueued_connectors: payload.enqueued_connectors ?? [],
        canonical_backlog_task_id: payload.canonical_backlog_task_id,
        deleted_rows_total: payload.deleted_rows_total ?? 0,
      });
      refreshOverviewPulse();
    },
  });

  const health = useMemo(() => {
    const o = overviewQ.data;
    if (!o) {
      return {
        badgeText: "…",
        tone: "neutral" as const,
        hasFailed: false,
        schedulerOffEnv: false,
        operatorPaused: false,
      };
    }
    const hasFailed = o.connectors.some((c) => c.latest_run?.status === "FAILED");
    const mode = o.global_scheduler.operator_mode_label;
    const schedulerOffEnv = !o.global_scheduler.env_scheduler_enabled;
    const operatorPaused = o.global_scheduler.paused_via_redis;

    if (hasFailed) {
      return {
        badgeText: `Degraded · ${mode}`,
        tone: "warn" as const,
        hasFailed: true,
        schedulerOffEnv,
        operatorPaused,
      };
    }
    if (schedulerOffEnv) {
      return {
        badgeText: mode,
        tone: "warn" as const,
        hasFailed: false,
        schedulerOffEnv: true,
        operatorPaused,
      };
    }
    if (operatorPaused) {
      return {
        badgeText: mode,
        tone: "warn" as const,
        hasFailed: false,
        schedulerOffEnv: false,
        operatorPaused: true,
      };
    }
    return {
      badgeText: mode,
      tone: "ok" as const,
      hasFailed: false,
      schedulerOffEnv: false,
      operatorPaused: false,
    };
  }, [overviewQ.data]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (overviewQ.isPending) return <p className="text-sm text-stone-600">Loading Cortex overview…</p>;
  if (overviewQ.isError) return <p className="text-sm text-red-700">{(overviewQ.error as Error).message}</p>;

  const o = overviewQ.data;
  const wt = o.worker_telemetry;
  const dedupe = o.duplicate_prevention;
  const runnableConnectors = o.connectors
    .filter((c) => c.cortex_routed && c.connection_status === "active")
    .map((c) => c.connector);
  const failedRuns = recentRunsQ.data?.items.filter((r) => r.status === "FAILED").length ?? 0;
  const activeReplay = recentRunsQ.data?.items.filter((r) => r.replay_mode && r.status === "RUNNING").length ?? 0;
  const replayWorkers = wt.replay_queue_workers;
  const replayQueueValue =
    activeReplay > 0 ? "replaying" : replayWorkers > 0 ? "ready" : "idle";
  const replayQueueTone =
    activeReplay > 0 ? "warn" : replayWorkers > 0 ? ("ok" as const) : ("warn" as const);
  const replayQueueDetail =
    activeReplay > 0
      ? `${activeReplay} replay run(s) currently active`
      : replayWorkers > 0
        ? "No active replay jobs right now; worker is listening."
        : "No worker currently listening on cortex_replay.";
  const rowsToday =
    rawStatsQ.data?.resources
      .filter((r) => {
        if (!r.newest_fetched_at) return false;
        const d = new Date(r.newest_fetched_at);
        const now = new Date();
        return (
          d.getUTCFullYear() === now.getUTCFullYear() &&
          d.getUTCMonth() === now.getUTCMonth() &&
          d.getUTCDate() === now.getUTCDate()
        );
      })
      .reduce((acc, r) => acc + r.row_count, 0) ?? 0;

  const latestSuccess = recentRunsQ.data?.items.find((r) => r.status === "COMPLETED");
  const lagThresholdSec = Math.max(
    o.global_scheduler.min_gap_seconds * 3,
    o.global_scheduler.beat_interval_seconds * 2,
  );
  const routedActiveConnectors = o.connectors.filter(
    (c) => c.cortex_routed && c.connection_status === "active",
  );
  const laggingConnectors = routedActiveConnectors.filter((c) => {
    if (!c.checkpoint_last_incremental_at) return true;
    const ageSec = (Date.now() - new Date(c.checkpoint_last_incremental_at).getTime()) / 1000;
    return Number.isFinite(ageSec) && ageSec > lagThresholdSec;
  });

  const liveQueueValue =
    o.global_scheduler.env_scheduler_enabled && !o.global_scheduler.paused_via_redis ? "active" : "inactive";
  const liveQueueDetail = !o.global_scheduler.env_scheduler_enabled
    ? `Beat does not enqueue: CORTEX_INGESTION_SCHEDULER_ENABLED is false in server config (defaults to false). Set it true on API + Celery Beat + workers, redeploy. Manual Ingest all connectors still queues tasks if workers listen on cortex_live. interval ${o.global_scheduler.beat_interval_seconds}s / gap ${o.global_scheduler.min_gap_seconds}s`
    : o.global_scheduler.paused_via_redis
      ? `Operator pause (Redis). Use Resume ingestion. interval ${o.global_scheduler.beat_interval_seconds}s / gap ${o.global_scheduler.min_gap_seconds}s`
      : `interval ${o.global_scheduler.beat_interval_seconds}s / gap ${o.global_scheduler.min_gap_seconds}s`;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Cortex Overview</h2>
            <p className="text-sm text-stone-600">{o.company_name}</p>
          </div>
          <StatusBadge tone={health.tone}>{health.badgeText}</StatusBadge>
        </div>
        {health.schedulerOffEnv ? (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
            <p className="font-medium">Scheduled ingestion is off in this deployment</p>
            <p className="mt-1 text-amber-900/95">
              <span className="font-mono">CORTEX_INGESTION_SCHEDULER_ENABLED</span> is not true, so Celery Beat will
              not enqueue periodic syncs. <strong>Resume ingestion</strong> only clears an operator pause in Redis —
              it cannot turn on the env flag. Set the variable to <span className="font-mono">true</span> in your AWS
              task/Beanstalk/env config, restart API + Beat + workers, then refresh this page.
            </p>
          </div>
        ) : null}
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {statCard("Cortex status", health.badgeText, health.tone)}
          {statCard(
            "Live queue health",
            liveQueueValue,
            o.global_scheduler.env_scheduler_enabled && !o.global_scheduler.paused_via_redis ? "ok" : "warn",
            liveQueueDetail,
          )}
          {statCard("Replay queue health", replayQueueValue, replayQueueTone, replayQueueDetail)}
          {statCard(
            "Active workers",
            String(wt.worker_count),
            wt.status === "ok" && wt.worker_count > 0 ? "ok" : "warn",
            wt.status === "ok"
              ? `live queue: ${wt.live_queue_workers}, replay queue: ${wt.replay_queue_workers}`
              : wt.detail ?? "Worker telemetry unavailable.",
          )}
          {statCard("Failed runs", String(failedRuns), failedRuns > 0 ? "warn" : "ok", "in last 25 runs")}
          {statCard(
            "Last successful ingestion",
            latestSuccess ? new Date(latestSuccess.started_at).toLocaleString() : "none",
            latestSuccess ? "ok" : "warn",
          )}
          {statCard("Raw rows today", String(rowsToday), rowsToday > 0 ? "ok" : "neutral")}
          {statCard("Replay jobs active", String(activeReplay), activeReplay > 0 ? "warn" : "neutral")}
          {statCard(
            "Duplicate prevention ratio",
            dedupe.ratio_percent == null ? "n/a" : `${dedupe.ratio_percent}%`,
            dedupe.status === "ok" ? "ok" : dedupe.status === "warn" ? "warn" : "neutral",
            dedupe.detail ??
              `rows ${dedupe.live_rows_examined}, duplicate groups ${dedupe.duplicate_groups}, excess rows ${dedupe.duplicate_rows_excess}`,
          )}
          {statCard(
            "Checkpoint lag warnings",
            laggingConnectors.length > 0 ? "attention" : "clear",
            laggingConnectors.length > 0 ? "warn" : "ok",
            `${laggingConnectors.length} of ${routedActiveConnectors.length} active routed connectors over threshold (${lagThresholdSec}s)`,
          )}
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-medium text-stone-900">Operational actions</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-40"
            disabled={bulkSyncMut.isPending || runnableConnectors.length === 0}
            onClick={() => bulkSyncMut.mutate(runnableConnectors)}
          >
            {bulkSyncMut.isPending ? "Queueing…" : "Ingest all connectors"}
          </button>
          <button
            type="button"
            className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-40"
            disabled={bulkReplayMut.isPending || runnableConnectors.length === 0}
            onClick={() => bulkReplayMut.mutate(runnableConnectors)}
          >
            {bulkReplayMut.isPending ? "Queueing…" : "Replay all connectors"}
          </button>
          <button
            type="button"
            className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-100 disabled:opacity-40"
            disabled={flushRerunMut.isPending}
            onClick={() => {
              const typed = window.prompt(
                `Dangerous action.\n\nType exactly:\n${CORTEX_FLUSH_RERUN_CONFIRM_PHRASE}`,
              );
              if (typed == null) return;
              flushRerunMut.mutate(typed.trim());
            }}
          >
            {flushRerunMut.isPending ? "Submitting…" : "Flush + rerun to Identity"}
          </button>
          <button
            type="button"
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100 disabled:opacity-40"
            disabled={pauseMut.isPending || o.global_scheduler.paused_via_redis}
            title="Writes operator pause to Redis; Beat skips enqueue while paused (only when scheduler env is enabled)."
            onClick={() => pauseMut.mutate(true)}
          >
            Pause ingestion
          </button>
          <button
            type="button"
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100 disabled:opacity-40"
            disabled={pauseMut.isPending || !o.global_scheduler.paused_via_redis}
            title={
              o.global_scheduler.paused_via_redis
                ? "Clear operator pause in Redis so Beat can enqueue again."
                : "Disabled unless operator pause is active. If ingestion looks stopped but this is greyed out, the scheduler is likely off in env (CORTEX_INGESTION_SCHEDULER_ENABLED), not paused in Redis."
            }
            onClick={() => pauseMut.mutate(false)}
          >
            Resume ingestion
          </button>
          <button
            type="button"
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100"
            onClick={() => navigate(`/admin/tenants/${tenantId}/cortex/ingestion?tab=verification`)}
          >
            Run verification
          </button>
          <button
            type="button"
            className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100"
            onClick={() => navigate(`/admin/tenants/${tenantId}/cortex/ingestion?tab=raw-explorer`)}
          >
            Open raw explorer
          </button>
        </div>
        {lastActionSummary ? (
          <div className="mt-3 rounded-md border border-stone-200 bg-stone-50 p-3 text-xs text-stone-700">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone={lastActionSummary.failCount > 0 ? "warn" : "ok"}>
                {lastActionSummary.kind === "sync" ? "ingest enqueue" : "replay enqueue"}
              </StatusBadge>
              <span>
                queued {lastActionSummary.okCount}, failed {lastActionSummary.failCount}
              </span>
            </div>
            {lastActionSummary.okConnectors.length > 0 ? (
              <p className="mt-1">queued: {lastActionSummary.okConnectors.map(titleConnector).join(", ")}</p>
            ) : null}
            {lastActionSummary.failures.length > 0 ? (
              <ul className="mt-1 space-y-1">
                {lastActionSummary.failures.map((f) => (
                  <li key={`${lastActionSummary.kind}-${f.connector}`}>
                    {titleConnector(f.connector)}: {f.detail ?? "enqueue failed"}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        {flushRerunMut.isError ? (
          <p className="mt-2 text-xs text-red-700">{(flushRerunMut.error as Error).message}</p>
        ) : null}
        {lastFlushRerunSummary ? (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-900">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="warn">flush + rerun to Identity accepted</StatusBadge>
              <span>deleted rows: {lastFlushRerunSummary.deleted_rows_total}</span>
            </div>
            <p className="mt-1">
              enqueued connectors:{" "}
              {lastFlushRerunSummary.enqueued_connectors.length > 0
                ? lastFlushRerunSummary.enqueued_connectors.map(titleConnector).join(", ")
                : "none"}
            </p>
            <p className="mt-1">
              pipeline task (ingest → canonical → Identity backfill):{" "}
              {lastFlushRerunSummary.canonical_backlog_task_id ?? "not enqueued"}
            </p>
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Connector pulse</h3>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {o.connectors.map((c) => (
            <button
              key={c.connector}
              type="button"
              onClick={() => navigate(`/admin/tenants/${tenantId}/cortex/ingestion?tab=connectors`)}
              className="rounded-lg border border-stone-200 bg-stone-50 p-3 text-left hover:bg-stone-100"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-stone-900">{titleConnector(c.connector)}</p>
                <StatusBadge
                  tone={!c.cortex_routed ? "neutral" : c.latest_run?.status === "FAILED" ? "bad" : "ok"}
                >
                  {!c.cortex_routed ? "not routed" : c.latest_run?.status ?? "idle"}
                </StatusBadge>
              </div>
              <p className="mt-1 text-xs text-stone-600">
                checkpoint: {c.checkpoint_last_incremental_at ? new Date(c.checkpoint_last_incremental_at).toLocaleString() : "n/a"}
              </p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
