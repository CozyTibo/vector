import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE } from "../adminConstants";
import { START_PHASE_OPTIONS } from "../cortex/pipelineTypes";
import { invalidateOperatorOverviewCaches } from "./useOperatorOverview";

type Props = {
  runnableConnectors: string[];
};

export function OperatorCompactActions({ runnableConnectors }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [startPhase, setStartPhase] = useState("canonical");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runMut = useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      return adminJson<{ mode: string; hint?: string }>(
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
        setMessage(data.hint ?? "Sync queued.");
      } else if (data.mode === "from_phase") {
        setMessage(`Execution rerun enqueued from ${startPhase}.`);
      }
      invalidateOperatorOverviewCaches(qc, tenantId);
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Actions</p>
      <p className="mt-1 text-xs text-stone-600">Safe operator actions only. Destructive flush lives on Runtime (R2).</p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
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
          Run from ingestion
        </button>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block text-xs text-stone-600">
            Run from phase
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
            Run
          </button>
        </div>
        <Link
          to={`/admin/tenants/${tenantId}/cortex/graph`}
          className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 no-underline hover:bg-stone-50"
        >
          Open inspect
        </Link>
      </div>
      {message ? <p className="mt-2 text-xs text-green-800">{message}</p> : null}
      {error ? <p className="mt-2 text-xs text-red-700">{error}</p> : null}
    </section>
  );
}
