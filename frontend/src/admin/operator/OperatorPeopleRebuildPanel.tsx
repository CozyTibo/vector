import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";

import { REBUILD_IDENTITIES_CONFIRM_PHRASE } from "../adminConstants";
import { StatusBadge } from "../ui/StatusBadge";
import {
  formatActionFeedback,
  pendingActionFeedback,
  type ActionFeedback,
} from "./actionFeedback";
import { postOperatorAction } from "./fetchOperator";
import { invalidateOperatorCaches } from "./useOperatorRuntime";

function confirmPhrase(expected: string): string | null {
  const typed = window.prompt(`Type exactly:\n${expected}`);
  if (typed == null) return null;
  const trimmed = typed.trim();
  return trimmed === expected ? trimmed : "";
}

function feedbackToneClass(tone: ActionFeedback["tone"]): string {
  switch (tone) {
    case "ok":
      return "border-green-200 bg-green-50 text-green-950";
    case "warn":
      return "border-amber-200 bg-amber-50 text-amber-950";
    case "error":
      return "border-red-200 bg-red-50 text-red-950";
    case "pending":
      return "border-indigo-200 bg-indigo-50 text-indigo-950";
  }
}

export function OperatorPeopleRebuildPanel() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [feedback, setFeedback] = useState<ActionFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rebuildMut = useMutation({
    mutationFn: () =>
      postOperatorAction(
        tenantId,
        {
          action: "rebuild_identities",
          confirmation: REBUILD_IDENTITIES_CONFIRM_PHRASE,
        },
        { timeoutMs: 120_000 },
      ),
    onSuccess: (data) => {
      setError(null);
      setFeedback(formatActionFeedback(data));
      invalidateOperatorCaches(qc, tenantId);
      void qc.invalidateQueries({ queryKey: ["operator-people-directory", tenantId] });
    },
    onError: (e: Error) => {
      setFeedback(null);
      setError(e.message === "confirmation_mismatch" ? "Confirmation phrase did not match." : e.message);
    },
  });

  const runRebuild = () => {
    const confirmed = confirmPhrase(REBUILD_IDENTITIES_CONFIRM_PHRASE);
    if (confirmed == null) return;
    if (confirmed === "") {
      setFeedback(null);
      setError("Confirmation phrase did not match.");
      return;
    }
    setError(null);
    setFeedback(pendingActionFeedback("rebuild_identities"));
    rebuildMut.mutate();
  };

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-stone-900">Rebuild identities</p>
          <p className="mt-1 text-xs text-stone-600">
            Clears org handles and link candidates, then rescans existing canonical anchors to reconstruct people.
            Raw ingestion and canonical materialization are untouched. Graph and downstream phases restart afterward.
          </p>
        </div>
        <button
          type="button"
          className="shrink-0 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-100 disabled:opacity-40"
          disabled={rebuildMut.isPending || !tenantId}
          onClick={runRebuild}
        >
          {rebuildMut.isPending ? "Rebuilding…" : "Rebuild from anchors"}
        </button>
      </div>

      {feedback ? (
        <div
          className={`mt-4 rounded-lg border px-4 py-3 text-sm ${feedbackToneClass(feedback.tone)}`}
          role="status"
          aria-live="polite"
        >
          <div className="flex flex-wrap items-start gap-2">
            <StatusBadge tone={feedback.tone === "pending" ? "neutral" : feedback.tone === "ok" ? "ok" : "warn"}>
              {feedback.tone === "pending" ? "running" : feedback.tone}
            </StatusBadge>
            <div className="min-w-0 flex-1">
              <p className="font-medium">{feedback.title}</p>
              {feedback.detail ? <p className="mt-1 text-xs opacity-90">{feedback.detail}</p> : null}
              {feedback.tone === "ok" ? (
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/runtime`}
                  className="mt-2 inline-block text-xs font-medium text-indigo-700 no-underline hover:underline"
                >
                  Open Runtime to watch downstream progress →
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}
