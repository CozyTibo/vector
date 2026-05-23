import type { DeferralOmissionPosture } from "./pipelineTypes";
import { StatusBadge } from "../ui/StatusBadge";
import { SectionSkeleton } from "./SectionSkeleton";

export function DeferralOmissionCard({
  omission,
  loading,
}: {
  omission: DeferralOmissionPosture | undefined;
  loading?: boolean;
}) {
  if (loading && !omission) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-5 shadow-sm">
        <SectionSkeleton variant="cards" />
      </section>
    );
  }
  if (!omission || omission.enabled === false) return null;

  const permanent = Number(omission.permanent_orphan_count ?? 0);
  const deferTotal = Number(omission.deferral_total ?? 0);
  const retryReady = Number(omission.deferred_retry_ready ?? 0);
  const bounded = Boolean(omission.is_bounded_omission_not_failure);

  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-amber-950">Deferral omission posture</h2>
          <p className="mt-1 text-sm text-amber-900/90">
            {omission.summary ??
              "Permanent topology orphans are bounded omission — not a failure to drain deferrals to zero."}
          </p>
        </div>
        <StatusBadge tone={bounded ? "ok" : "warn"}>
          {bounded ? "Bounded omission" : "Review deferrals"}
        </StatusBadge>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-amber-100 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-amber-800">
            Permanent orphans
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-amber-950">
            {permanent.toLocaleString()}
          </dd>
          <dd className="text-xs text-amber-800">
            Ref ~{Number(omission.fizzer_reference_count ?? 466).toLocaleString()} (Fizzer)
          </dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Deferral total
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{deferTotal.toLocaleString()}</dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Retry-ready
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{retryReady.toLocaleString()}</dd>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Posture</dt>
          <dd className="mt-1 text-sm font-medium text-stone-800">
            {omission.posture?.replace(/_/g, " ") ?? "—"}
          </dd>
        </div>
      </dl>

      {omission.chase_zero_deferrals_forbidden ? (
        <p className="mt-3 text-xs text-amber-900">
          Do not use deferral_total → 0 as a pass/fail gate. Optimize drainable routable and
          retry-ready deferrals instead.
          {omission.runbook_path ? (
            <>
              {" "}
              Runbook: <span className="font-mono text-[11px]">{omission.runbook_path}</span>
            </>
          ) : null}
        </p>
      ) : null}
    </section>
  );
}
