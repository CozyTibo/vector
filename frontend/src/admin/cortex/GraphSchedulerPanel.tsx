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
      void qc.invalidateQueries({ queryKey: ["admin-cortex-graph"] });
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
      void qc.invalidateQueries({ queryKey: ["admin-cortex-graph"] });
      setRebuildConfirm("");
    },
  });

  const data = readinessQ.data;
  if (!data) return null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Graph projection</h2>
      <p className="mt-1 text-sm text-stone-600">
        Extractor v{data.extractor_version} · {data.active_relationship_count.toLocaleString()} active links ·{" "}
        {data.dirty_queue_pending} dirty
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          className="min-w-[16rem] flex-1 rounded border border-stone-200 px-2 py-1 text-sm"
          placeholder={TRIGGER_PHRASE}
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
        <input
          type="text"
          className="min-w-[16rem] flex-1 rounded border border-stone-200 px-2 py-1 text-sm"
          placeholder={REBUILD_PHRASE}
          value={rebuildConfirm}
          onChange={(e) => setRebuildConfirm(e.target.value)}
        />
        <button
          type="button"
          className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-800 disabled:opacity-50"
          disabled={rebuildConfirm !== REBUILD_PHRASE || rebuildM.isPending}
          onClick={() => rebuildM.mutate()}
        >
          Rebuild
        </button>
      </div>
    </section>
  );
}
