import type { ContinuityStatus } from "./pipelineTypes";
import { StatusBadge } from "../ui/StatusBadge";

function stateTone(
  state: ContinuityStatus["state"],
): "ok" | "warn" | "bad" | "neutral" {
  if (state === "AUTONOMOUS") return "ok";
  if (state === "OPERATOR_RECOVERY" || state === "DEGRADED") return "warn";
  return "bad";
}

function laneTone(lane: string): "ok" | "warn" | "bad" | "neutral" {
  if (lane === "HEALTHY") return "ok";
  if (lane === "WAITING" || lane === "DEGRADED") return "warn";
  if (lane === "BLOCKED") return "bad";
  return "neutral";
}

export function ContinuityStatusCard({
  status,
  loading,
}: {
  status: ContinuityStatus | undefined;
  loading?: boolean;
}) {
  if (loading && !status) {
    return (
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="h-24 animate-pulse rounded-lg bg-stone-100" aria-hidden />
      </section>
    );
  }
  if (!status) return null;

  const soak = status.aa_continuity_soak;
  const soakLine =
    soak?.active && soak.hours_elapsed != null && soak.hours_required
      ? `AA continuity soak: ${soak.hours_elapsed}h / ${soak.hours_required}h`
      : null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">Cortex continuity status</h2>
          <p className="mt-1 text-sm text-stone-600">
            Operational truth — autonomous execution health, not substrate vanity counts.
          </p>
        </div>
        <StatusBadge tone={stateTone(status.state)}>
          {status.state_label || status.state.replace(/_/g, " ")}
        </StatusBadge>
      </div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Execution lane</dt>
          <dd className="mt-0.5">
            <StatusBadge tone={laneTone(status.execution_lane)}>{status.execution_lane}</StatusBadge>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Canonical lane</dt>
          <dd className="mt-0.5">
            <StatusBadge tone={laneTone(status.canonical_lane)}>{status.canonical_lane}</StatusBadge>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Last autonomous 05→08 chain
          </dt>
          <dd className="mt-0.5 font-medium text-stone-900">
            {status.last_full_chain_ago || "—"}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Last retrieval epoch</dt>
          <dd className="mt-0.5 font-medium text-stone-900">
            {status.last_retrieval_epoch_ago || "—"}
            {status.last_retrieval_epoch ? (
              <span className="block text-xs font-normal text-stone-500">{status.last_retrieval_epoch}</span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Last synthesis</dt>
          <dd className="mt-0.5 font-medium text-stone-900">{status.last_synthesis_ago || "—"}</dd>
        </div>
        {soakLine ? (
          <div className="sm:col-span-2 lg:col-span-3">
            <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Continuity soak</dt>
            <dd className="mt-0.5 font-medium text-stone-900">{soakLine}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
