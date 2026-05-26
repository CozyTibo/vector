import type { SubstrateTruth } from "./operatorTypes";

const STATUS_STYLES: Record<string, string> = {
  HEALTHY: "border-emerald-200 bg-emerald-50 text-emerald-900",
  DEGRADED: "border-amber-200 bg-amber-50 text-amber-950",
  BROKEN: "border-red-200 bg-red-50 text-red-900",
  STALLED: "border-stone-400 bg-stone-100 text-stone-900",
};

function Metric({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
      <div className="text-xs font-medium uppercase tracking-wide text-stone-500">{label}</div>
      <div className="mt-0.5 font-mono text-sm text-stone-900">{value ?? "—"}</div>
    </div>
  );
}

export function OperatorSubstrateTruthSection({ truth }: { truth: SubstrateTruth }) {
  const statusClass = STATUS_STYLES[truth.overall_status] ?? STATUS_STYLES.DEGRADED;
  const identity = truth.identity as {
    health?: { status?: string; reasons?: string[] };
    counts?: Record<string, number>;
    repair?: Record<string, unknown>;
  };
  const graph = (truth.graph_substrate ?? truth.graph) as {
    unique_auth_pairs?: number;
    isolated_pct?: number;
    promotion_rule_count?: number;
    dup_factor?: number | null;
  };
  const repair = identity.repair ?? {};
  const health = identity.health ?? {};

  return (
    <section className={`rounded-xl border p-4 shadow-sm ${statusClass}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Substrate truth</h2>
          <p className="mt-1 text-sm opacity-90">
            Authoritative ingest → materialize → identity → graph state. Trust this before phase receipts or
            edge counts.
          </p>
        </div>
        <span className="rounded-md border border-current px-2 py-1 font-mono text-sm font-semibold">
          {truth.overall_status}
        </span>
      </div>

      {truth.red_rules.length > 0 ? (
        <ul className="mt-3 list-inside list-disc text-sm">
          {truth.red_rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      ) : null}

      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Anchors" value={identity.counts?.identity_anchors} />
        <Metric label="Active entities" value={identity.counts?.org_entities_active} />
        <Metric label="Unique auth pairs" value={graph.unique_auth_pairs} />
        <Metric label="Promotion rules" value={graph.promotion_rule_count} />
        <Metric label="Isolated %" value={graph.isolated_pct != null ? `${graph.isolated_pct}%` : null} />
        <Metric label="Repair offset" value={`${repair.anchor_offset ?? 0} / ${repair.anchors_total ?? "?"}`} />
        <Metric
          label="Repair exhausted"
          value={repair.anchor_backfill_exhausted === true ? "yes" : repair.anchor_backfill_exhausted === false ? "no" : null}
        />
        <Metric label="Identity health" value={health.status} />
      </div>

      {truth.operator_guidance.length > 0 ? (
        <ul className="mt-4 space-y-1 text-sm">
          {truth.operator_guidance.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
