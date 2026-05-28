import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { useGraphReadiness } from "./useGraphReadiness";

const TRIGGER_PHRASE = "RUN GRAPH PROJECTION PASS";
const REBUILD_PHRASE = "REBUILD GRAPH PROJECTIONS";

export function GraphSchedulerPanel() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const readinessQ = useGraphReadiness();
  const [confirm, setConfirm] = useState("");
  const [rebuildConfirm, setRebuildConfirm] = useState("");

  const invalidateGraph = () => {
    void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-readiness", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-runs", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-relationships", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-stats", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-unresolved", tenantId] });
  };

  const triggerM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/graph/actions/trigger-pass`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation: confirm }),
        },
      );
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return res.json();
    },
    onSuccess: () => {
      invalidateGraph();
      setConfirm("");
    },
  });

  const rebuildM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/graph/actions/rebuild`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation: rebuildConfirm }),
        },
      );
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return res.json();
    },
    onSuccess: () => {
      invalidateGraph();
      setRebuildConfirm("");
    },
  });

  const data = readinessQ.data;
  const sched = data?.scheduler;
  if (!data || !sched) return null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Scheduler</h2>
      <p className="mt-1 text-sm text-stone-600">
        Orchestrator plans graph passes every {sched.orchestrator_interval_seconds ?? 120}s (lane cadence{" "}
        {sched.interval_seconds}s) · mode{" "}
        <span className="font-medium text-stone-800">{sched.enabled ? "Active" : "Off (env)"}</span>
        {sched.tenant_needs_work === false ? (
          <span className="text-stone-500"> · idle (no scheduled work)</span>
        ) : null}
        {sched.lane_stale ? <span className="font-medium text-rose-700"> · lane stale</span> : null}
        {data.canon_backlog ? (
          <span className="font-medium text-amber-800"> · blocked by canon backlog</span>
        ) : null}
      </p>
      <p className="mt-2 text-xs text-stone-500">
        Extractor v{data.extractor_version} · {data.active_relationship_count.toLocaleString()} active links ·{" "}
        {data.dirty_queue_pending} dirty ({data.dirty_queue_extract_pending} extract)
      </p>

      <div className="mt-3 rounded border border-amber-100 bg-amber-50/80 p-3">
        <p className="text-xs text-amber-950">
          Manual pass — type exactly: <code className="font-mono">{TRIGGER_PHRASE}</code>
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[260px] flex-1 rounded border border-amber-200 px-2 py-1.5 text-sm"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
          <button
            type="button"
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            disabled={confirm !== TRIGGER_PHRASE || triggerM.isPending}
            onClick={() => triggerM.mutate()}
          >
            Trigger pass
          </button>
        </div>
        {triggerM.isError ? (
          <p className="mt-2 text-xs text-red-700">{(triggerM.error as Error).message}</p>
        ) : null}
      </div>

      <div className="mt-3 rounded border border-stone-200 bg-stone-50/80 p-3">
        <p className="text-xs text-stone-700">
          Full rebuild — type exactly: <code className="font-mono">{REBUILD_PHRASE}</code>
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[260px] flex-1 rounded border border-stone-200 px-2 py-1.5 text-sm"
            value={rebuildConfirm}
            onChange={(e) => setRebuildConfirm(e.target.value)}
          />
          <button
            type="button"
            className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 disabled:opacity-50"
            disabled={rebuildConfirm !== REBUILD_PHRASE || rebuildM.isPending}
            onClick={() => rebuildM.mutate()}
          >
            Rebuild
          </button>
        </div>
        {rebuildM.isError ? (
          <p className="mt-2 text-xs text-red-700">{(rebuildM.error as Error).message}</p>
        ) : null}
      </div>
    </section>
  );
}
