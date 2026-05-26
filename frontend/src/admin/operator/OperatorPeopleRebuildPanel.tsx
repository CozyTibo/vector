import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";

import { REBUILD_IDENTITIES_CONFIRM_PHRASE } from "../adminConstants";
import { StatusBadge } from "../ui/StatusBadge";
import {
  formatActionFeedback,
  pendingActionFeedback,
  type ActionFeedback,
} from "./actionFeedback";
import { fetchOperatorRuntime, postOperatorAction } from "./fetchOperator";
import { invalidateOperatorCaches } from "./useOperatorRuntime";
import type { IdentitySubstrateHealth, IdentitySubstrateRepair } from "./operatorTypes";

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

function IdentityRepairProgress({
  health,
  repair,
}: {
  health: IdentitySubstrateHealth | null | undefined;
  repair: IdentitySubstrateRepair | null | undefined;
}) {
  if (!health && !repair) return null;
  const anchors = health?.metrics?.identity_anchors ?? repair?.anchors_total;
  const offset = repair?.anchor_offset ?? 0;
  const total = repair?.anchors_total ?? anchors;
  const exhausted = repair?.anchor_backfill_exhausted === true;
  const humans = health?.metrics?.active_human_actors;
  const pct =
    total && total > 0 ? Math.min(100, Math.round((offset / total) * 100)) : null;

  return (
    <div className="mt-3 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs text-stone-700">
      <p className="font-medium text-stone-900">Identity repair progress (live)</p>
      <ul className="mt-2 space-y-1">
        <li>
          Health: <span className="font-medium">{health?.status ?? "—"}</span>
          {health?.reasons?.length ? ` (${health.reasons.join(", ")})` : ""}
        </li>
        {total != null ? (
          <li>
            Anchors scanned: {offset.toLocaleString()}
            {total ? ` / ${total.toLocaleString()}` : ""}
            {exhausted ? " · exhausted" : " · in progress"}
          </li>
        ) : null}
        {pct != null && !exhausted ? (
          <li className="mt-1">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-stone-200">
              <div className="h-full rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
            </div>
          </li>
        ) : null}
        {humans != null ? <li>Human actors (org handles): {humans.toLocaleString()}</li> : null}
        {health?.metrics?.distinct_authoritative_promotion_rules != null ? (
          <li>
            Promotion rules in graph: {health.metrics.distinct_authoritative_promotion_rules}
          </li>
        ) : null}
      </ul>
    </div>
  );
}

export function OperatorPeopleRebuildPanel() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [feedback, setFeedback] = useState<ActionFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [watchRepair, setWatchRepair] = useState(false);

  const runtimeWatchQ = useQuery({
    queryKey: ["operator-runtime-repair-watch", tenantId],
    queryFn: () => fetchOperatorRuntime(tenantId),
    enabled: watchRepair && Boolean(tenantId),
    refetchInterval: watchRepair ? 5_000 : false,
  });

  const rebuildMut = useMutation({
    mutationFn: () =>
      postOperatorAction(
        tenantId,
        {
          action: "rebuild_identities",
          confirmation: REBUILD_IDENTITIES_CONFIRM_PHRASE,
        },
        { timeoutMs: 60_000 },
      ),
    onSuccess: (data) => {
      setError(null);
      setFeedback(formatActionFeedback(data));
      const enqueued = data.result?.enqueued === true;
      setWatchRepair(enqueued);
      if (!enqueued) {
        setWatchRepair(false);
      }
      invalidateOperatorCaches(qc, tenantId);
      void qc.invalidateQueries({ queryKey: ["operator-people-directory", tenantId] });
    },
    onError: (e: Error) => {
      setFeedback(null);
      setWatchRepair(false);
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
    setWatchRepair(true);
    rebuildMut.mutate();
  };

  const repairExhausted = runtimeWatchQ.data?.identity_substrate_repair?.anchor_backfill_exhausted === true;

  useEffect(() => {
    if (!repairExhausted) return;
    setWatchRepair(false);
    void qc.invalidateQueries({ queryKey: ["operator-people-directory", tenantId] });
  }, [repairExhausted, qc, tenantId]);

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-stone-900">Rebuild identities</p>
          <p className="mt-1 text-xs text-stone-600">
            Incrementally rescans canonical anchors into org handles and link candidates (no destructive wipe).
            Raw ingestion and canonical materialization are untouched. Graph downstream may restart after repair completes.
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
              {feedback.tone === "ok" || watchRepair ? (
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/runtime`}
                  className="mt-2 inline-block text-xs font-medium text-indigo-700 no-underline hover:underline"
                >
                  Open Runtime for full transition log →
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
      {watchRepair ? (
        <IdentityRepairProgress
          health={runtimeWatchQ.data?.identity_substrate_health}
          repair={runtimeWatchQ.data?.identity_substrate_repair}
        />
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}
