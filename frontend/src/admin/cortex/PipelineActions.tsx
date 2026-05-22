import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import {
  CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE,
  CORTEX_FLUSH_RERUN_CONFIRM_PHRASE,
  CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
} from "../adminConstants";
import { StatusBadge } from "../ui/StatusBadge";
import { phaseSummaryDetailQueryKey } from "./usePhaseSummaryDetail";
import { pipelineOverviewSliceQueryKeys } from "./usePipelineOverview";
import { START_PHASE_OPTIONS, type OperatorPhase } from "./pipelineTypes";

type Props = {
  runnableConnectors: string[];
};

export function PipelineActions({ runnableConnectors }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [startPhase, setStartPhase] = useState("canonical");
  const [flushMode, setFlushMode] = useState<"derived_only" | "all">("derived_only");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => {
    for (const key of pipelineOverviewSliceQueryKeys(tenantId)) {
      void qc.invalidateQueries({ queryKey: key });
    }
    void qc.invalidateQueries({ queryKey: ["admin-cortex-pipeline-overview", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-phase-summary", tenantId] });
    const phases: OperatorPhase[] = [
      "ingestion",
      "canonical",
      "identity",
      "graph",
      "reconstruction",
      "retrieval",
      "synthesis",
    ];
    for (const p of phases) {
      void qc.invalidateQueries({ queryKey: phaseSummaryDetailQueryKey(tenantId, p) });
    }
    void qc.invalidateQueries({ queryKey: ["admin-cortex-ingestion", tenantId] });
  };

  const runMut = useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      return adminJson<{ mode: string; hint?: string; connector_syncs?: { ok: boolean }[] }>(
        `/admin/tenants/${tenantId}/cortex/pipeline/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
    },
    onSuccess: (data) => {
      setError(null);
      if (data.mode === "from_ingestion") {
        const n = data.connector_syncs?.filter((x) => x.ok).length ?? runnableConnectors.length;
        setMessage(data.hint ?? `Sync queued for ${n} connector(s).`);
      } else if (data.mode === "from_phase") {
        setMessage(`Execution rerun enqueued from ${startPhase}.`);
      } else if (data.mode === "flush_and_run") {
        setMessage(
          flushMode === "all"
            ? "Flushed raw + derived; sync and convergence rerun started."
            : "Flushed derived outputs; execution rerun from canonical enqueued.",
        );
      }
      invalidate();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Pipeline actions</p>
      <p className="mt-1 text-xs text-stone-600">Unified operator API — all mutations via pipeline/run.</p>
      <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
        <div>
          <button
            type="button"
            className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-40"
            disabled={runMut.isPending || runnableConnectors.length === 0}
            onClick={() =>
              runMut.mutate({
                mode: "from_ingestion",
                confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
              })
            }
          >
            {runMut.isPending ? "Queueing…" : "Run from ingestion"}
          </button>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block text-xs text-stone-600">
            Start from step
            <select
              className="mt-1 block rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={startPhase}
              onChange={(e) => setStartPhase(e.target.value)}
            >
              {START_PHASE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-40"
            disabled={runMut.isPending}
            onClick={() => runMut.mutate({ mode: "from_phase", start_phase: startPhase })}
          >
            {runMut.isPending ? "Starting…" : "Run"}
          </button>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block text-xs text-stone-600">
            Flush data
            <select
              className="mt-1 block rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              value={flushMode}
              onChange={(e) => setFlushMode(e.target.value as "derived_only" | "all")}
            >
              <option value="derived_only">Derived only (keep raw)</option>
              <option value="all">Everything (including raw)</option>
            </select>
          </label>
          <button
            type="button"
            className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-100 disabled:opacity-40"
            disabled={runMut.isPending}
            onClick={() => {
              const phrase =
                flushMode === "all" ? CORTEX_FLUSH_RERUN_CONFIRM_PHRASE : CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE;
              const typed = window.prompt(`Dangerous action.\n\nType exactly:\n${phrase}`);
              if (typed == null) return;
              if (typed.trim() !== phrase) {
                setError("Confirmation phrase did not match.");
                return;
              }
              runMut.mutate({
                mode: "flush_and_run",
                flush_mode: flushMode,
                confirmation: phrase,
              });
            }}
          >
            {runMut.isPending ? "Flushing…" : "Confirm flush"}
          </button>
        </div>
      </div>
      {message ? (
        <div className="mt-3 rounded-md border border-stone-200 bg-stone-50 p-3 text-xs text-stone-700">
          <StatusBadge tone="ok">ok</StatusBadge> <span className="ml-2">{message}</span>
        </div>
      ) : null}
      {error ? <p className="mt-2 text-xs text-red-700">{error}</p> : null}
    </section>
  );
}
