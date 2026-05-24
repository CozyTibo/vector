import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  CONTINUITY_P0_RECOVER_CONFIRM_PHRASE,
  CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE,
  CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE,
  CORTEX_FLUSH_RERUN_CONFIRM_PHRASE,
  CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
  CORTEX_RESTART_EXECUTION_CONFIRM_PHRASE,
  RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE,
} from "../adminConstants";
import { StatusBadge } from "../ui/StatusBadge";
import { START_PHASE_OPTIONS } from "./actionConstants";
import { postOperatorAction } from "./fetchOperator";
import type { OperatorActionKind, OperatorActionRequest } from "./operatorTypes";
import { invalidateOperatorCaches } from "./useOperatorRuntime";

type Variant = "compact" | "full";

type Props = {
  variant: Variant;
  runnableConnectors?: string[];
};

function confirmPhrase(expected: string): string | null {
  const typed = window.prompt(`Type exactly:\n${expected}`);
  if (typed == null) return null;
  return typed.trim() === expected ? expected : null;
}

function ActionHint({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 text-xs text-stone-500">{children}</p>;
}

export function OperatorActionPanel({ variant, runnableConnectors = [] }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [startPhase, setStartPhase] = useState("canonical");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const actionMut = useMutation({
    mutationFn: (body: OperatorActionRequest) => postOperatorAction(tenantId, body),
    onSuccess: (data) => {
      setError(null);
      setMessage(`Action ${data.action} completed.`);
      invalidateOperatorCaches(qc, tenantId);
    },
    onError: (e: Error) => {
      setMessage(null);
      setError(e.message === "confirmation_mismatch" ? "Confirmation phrase did not match." : e.message);
    },
  });

  const run = (body: OperatorActionRequest) => {
    setMessage(null);
    setError(null);
    actionMut.mutate(body);
  };

  const runConfirmed = (action: OperatorActionKind, phrase: string, extra: Partial<OperatorActionRequest> = {}) => {
    const confirmed = confirmPhrase(phrase);
    if (confirmed == null) {
      setError("Confirmation phrase did not match.");
      return;
    }
    run({ action, confirmation: confirmed, ...extra });
  };

  const isCompact = variant === "compact";
  const btnPrimary =
    "rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-40";
  const btnSecondary =
    "rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-40";
  const btnWarn =
    "rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-100 disabled:opacity-40";
  const btnDanger =
    "rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-100 disabled:opacity-40";

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Pipeline actions</p>
      <p className="mt-1 text-xs text-stone-600">
        Re-run substrate phases after code or config changes. Destructive actions require typing a confirmation phrase.
      </p>

      <div className="mt-4 flex flex-col gap-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Reprocess substrate</p>
          <ActionHint>
            Keeps raw ingestion rows. Clears canonical → synthesis derived state and reruns the full phase chain from
            canonicalization.
          </ActionHint>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className={btnWarn}
              disabled={actionMut.isPending}
              onClick={() => runConfirmed("flush_derived", CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE)}
            >
              Flush derived + rerun from canonical
            </button>
            <button
              type="button"
              className={btnSecondary}
              disabled={actionMut.isPending}
              onClick={() => run({ action: "run_from_phase", start_phase: "canonical" })}
            >
              Rerun from canonical (no flush)
            </button>
          </div>
        </div>

        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Ingestion</p>
          <ActionHint>Queues connector syncs, then marks the tenant dirty for execution convergence.</ActionHint>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <button
              type="button"
              className={btnPrimary}
              disabled={actionMut.isPending || runnableConnectors.length === 0}
              onClick={() => runConfirmed("run_from_ingestion", CORTEX_MANUAL_SYNC_CONFIRM_PHRASE)}
            >
              Run from ingestion
            </button>
          </div>
        </div>

        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Run from phase</p>
          <ActionHint>Restart the pipeline at a specific phase without flushing derived data first.</ActionHint>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <label className="block text-xs text-stone-600">
              Start phase
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
              className={btnSecondary}
              disabled={actionMut.isPending}
              onClick={() => run({ action: "run_from_phase", start_phase: startPhase })}
            >
              Run from {START_PHASE_OPTIONS.find((o) => o.value === startPhase)?.label ?? startPhase}
            </button>
          </div>
        </div>

        {!isCompact ? (
          <>
            <div className="border-t border-stone-100 pt-4">
              <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Execution recovery</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={btnSecondary}
                  disabled={actionMut.isPending}
                  onClick={() =>
                    runConfirmed("restart_execution", CORTEX_RESTART_EXECUTION_CONFIRM_PHRASE, {
                      start_phase: startPhase,
                    })
                  }
                >
                  Restart execution
                </button>
                <button
                  type="button"
                  className={btnSecondary}
                  disabled={actionMut.isPending}
                  onClick={() =>
                    runConfirmed("clear_derived", CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE, {
                      start_phase: startPhase,
                    })
                  }
                >
                  Clear derived (no rerun)
                </button>
                <button
                  type="button"
                  className={btnWarn}
                  disabled={actionMut.isPending}
                  onClick={() => runConfirmed("p0_recover", CONTINUITY_P0_RECOVER_CONFIRM_PHRASE)}
                >
                  P0 recover
                </button>
              </div>
            </div>

            <div className="border-t border-stone-100 pt-4">
              <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Destructive reset</p>
              <ActionHint>
                Flush all also deletes raw ingestion and re-syncs connectors — use only when you need a full wipe.
              </ActionHint>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={btnDanger}
                  disabled={actionMut.isPending}
                  onClick={() => runConfirmed("flush_all", CORTEX_FLUSH_RERUN_CONFIRM_PHRASE)}
                >
                  Flush raw + derived + rerun
                </button>
                <button
                  type="button"
                  className={btnDanger}
                  disabled={actionMut.isPending}
                  onClick={() =>
                    runConfirmed("rebuild_retrieval_index", RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE)
                  }
                >
                  Rebuild retrieval index
                </button>
              </div>
            </div>
          </>
        ) : (
          <p className="text-xs text-stone-500">
            Full recovery and raw flush live on{" "}
            <Link to={`/admin/tenants/${tenantId}/cortex/runtime`} className="font-medium text-indigo-700">
              Runtime
            </Link>
            .
          </p>
        )}
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
