import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { readErrorDetail } from "../../lib/canonicalApi";
import {
  CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE,
  CORTEX_FLUSH_RERUN_CONFIRM_PHRASE,
  CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
} from "../adminConstants";
import { StatusBadge } from "../ui/StatusBadge";
import { START_PHASE_OPTIONS } from "./pipelineTypes";

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
    void qc.invalidateQueries({ queryKey: ["admin-cortex-execution", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
    void qc.invalidateQueries({ queryKey: ["admin-cortex-ingestion", tenantId] });
  };

  const runFromIngestionMut = useMutation({
    mutationFn: async () => {
      const results = await Promise.all(
        runnableConnectors.map(async (connector) => {
          const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ connector, confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE }),
          });
          return { connector, ok: res.ok, detail: res.ok ? null : await readErrorDetail(res) };
        }),
      );
      return results;
    },
    onSuccess: (results) => {
      const failed = results.filter((r) => !r.ok);
      setError(failed.length ? failed.map((f) => `${f.connector}: ${f.detail}`).join("; ") : null);
      setMessage(
        failed.length
          ? `Sync queued for ${results.length - failed.length} connector(s); ${failed.length} failed. Convergence enqueues after ingest.`
          : `Sync queued for ${results.length} connector(s). Engine marks dirty and runs convergence after ingest.`,
      );
      invalidate();
    },
    onError: (e: Error) => setError(e.message),
  });

  const startFromStepMut = useMutation({
    mutationFn: async () => {
      const opt = START_PHASE_OPTIONS.find((o) => o.value === startPhase);
      if (!opt) throw new Error("invalid_start_phase");
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/execution/rerun?from_phase=${encodeURIComponent(opt.apiPhase)}`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      setMessage(`Execution rerun enqueued from ${startPhase}.`);
      setError(null);
      invalidate();
    },
    onError: (e: Error) => setError(e.message),
  });

  const flushMut = useMutation({
    mutationFn: async () => {
      if (flushMode === "all") {
        const clearRes = await adminFetch(
          `/admin/tenants/${tenantId}/cortex/execution/clear?from_phase=CANONICAL&flush_all=true`,
          { method: "POST" },
        );
        if (!clearRes.ok) throw new Error(await readErrorDetail(clearRes));
        const results = await Promise.all(
          runnableConnectors.map(async (connector) => {
            const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ connector, confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE }),
            });
            return res.ok;
          }),
        );
        if (results.every((x) => !x) && runnableConnectors.length > 0) {
          throw new Error("connector_sync_failed");
        }
        const rerunRes = await adminFetch(
          `/admin/tenants/${tenantId}/cortex/execution/rerun?from_phase=CANONICAL`,
          { method: "POST" },
        );
        if (!rerunRes.ok) throw new Error(await readErrorDetail(rerunRes));
        return { mode: "all" };
      }
      const clearRes = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/execution/clear?from_phase=CANONICAL`,
        { method: "POST" },
      );
      if (!clearRes.ok) throw new Error(await readErrorDetail(clearRes));
      const rerunRes = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/execution/rerun?from_phase=CANONICAL`,
        { method: "POST" },
      );
      if (!rerunRes.ok) throw new Error(await readErrorDetail(rerunRes));
      return { mode: "derived_only" };
    },
    onSuccess: (payload) => {
      setMessage(
        payload.mode === "all"
          ? "Flushed raw + derived; sync and convergence rerun started."
          : "Flushed derived outputs; execution rerun from canonical enqueued.",
      );
      setError(null);
      invalidate();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Pipeline actions</p>
      <p className="mt-1 text-xs text-stone-600">All mutations use the execution engine (no bypass transforms).</p>
      <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
        <div>
          <button
            type="button"
            className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-40"
            disabled={runFromIngestionMut.isPending || runnableConnectors.length === 0}
            onClick={() => runFromIngestionMut.mutate()}
          >
            {runFromIngestionMut.isPending ? "Queueing…" : "Run from ingestion"}
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
            disabled={startFromStepMut.isPending}
            onClick={() => startFromStepMut.mutate()}
          >
            {startFromStepMut.isPending ? "Starting…" : "Run"}
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
            disabled={flushMut.isPending}
            onClick={() => {
              const phrase =
                flushMode === "all" ? CORTEX_FLUSH_RERUN_CONFIRM_PHRASE : CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE;
              const typed = window.prompt(`Dangerous action.\n\nType exactly:\n${phrase}`);
              if (typed == null) return;
              if (typed.trim() !== phrase) {
                setError("Confirmation phrase did not match.");
                return;
              }
              flushMut.mutate();
            }}
          >
            {flushMut.isPending ? "Flushing…" : "Confirm flush"}
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
