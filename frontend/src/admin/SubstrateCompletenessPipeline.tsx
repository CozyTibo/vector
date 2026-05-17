import { Link } from "react-router-dom";

import { StatusBadge } from "./ui/StatusBadge";

export type SubstrateCompletenessStage = {
  stage_id: string;
  label: string;
  total_objects: number;
  success_percent: number;
  degraded_percent: number;
  unresolved_percent: number;
  intentionally_excluded_count?: number;
  replay_posture: string;
  substrate_state: string;
  last_successful_at: string | null;
  drift_warnings: string[];
  omission_classes: Record<string, number>;
  detail_route: string;
};

export type SubstrateCompletenessLedger = {
  substrate_state: string;
  substrate_replay_posture: string;
  pipeline_stages: SubstrateCompletenessStage[];
  degradation_propagation: {
    propagation_chain: Array<{
      from_stage: string;
      to_stage: string;
      explanation_summary: string;
    }>;
  };
};

function toneForState(state: string): "ok" | "warn" | "bad" | "neutral" {
  if (state === "healthy") return "ok";
  if (state === "degraded") return "warn";
  if (state === "critical") return "bad";
  return "neutral";
}

function StageCard({ stage }: { stage: SubstrateCompletenessStage }) {
  const omissions = Object.entries(stage.omission_classes || {}).filter(([, n]) => n > 0);
  const neverIndexed =
    stage.stage_id === "retrieval" &&
    (stage.omission_classes?.retrieval_index_never_built ?? 0) > 0;
  return (
    <Link
      to={stage.detail_route}
      className={[
        "block min-w-[148px] shrink-0 rounded-lg border bg-white p-3 shadow-sm transition hover:border-indigo-300 hover:shadow",
        neverIndexed ? "border-violet-300 ring-1 ring-violet-200" : "border-stone-200",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-600">{stage.label}</p>
        <StatusBadge tone={toneForState(stage.substrate_state)}>{stage.substrate_state}</StatusBadge>
      </div>
      <p className="mt-2 text-2xl font-semibold text-stone-900">{stage.total_objects}</p>
      <p className="text-xs text-stone-500">objects</p>
      <dl className="mt-3 space-y-1 text-xs text-stone-600">
        <div className="flex justify-between">
          <dt>Success</dt>
          <dd>{stage.success_percent}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Degraded</dt>
          <dd className={stage.degraded_percent > 0 ? "text-amber-700" : ""}>{stage.degraded_percent}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Unresolved</dt>
          <dd className={stage.unresolved_percent > 0 ? "text-red-700" : ""}>
            {stage.unresolved_percent}%
          </dd>
        </div>
        {(stage.intentionally_excluded_count ?? 0) > 0 && (
          <div className="flex justify-between">
            <dt>{stage.stage_id === "traversal" ? "Pending walks" : "Pending"}</dt>
            <dd className="text-stone-500">{stage.intentionally_excluded_count}</dd>
          </div>
        )}
        <div className="flex justify-between">
          <dt>Replay</dt>
          <dd className="font-mono">{stage.replay_posture}</dd>
        </div>
      </dl>
      {omissions.length > 0 && (
        <ul className="mt-2 max-h-20 overflow-auto text-[10px] text-amber-900">
          {omissions.map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
        </ul>
      )}
    </Link>
  );
}

export function SubstrateCompletenessPipeline({ ledger }: { ledger: SubstrateCompletenessLedger }) {
  const chain = ledger.degradation_propagation?.propagation_chain ?? [];
  const stages = ledger.pipeline_stages ?? [];
  const missingRetrieval = !stages.some((s) => s.stage_id === "retrieval");

  return (
    <section className="rounded-xl border border-stone-200 bg-stone-50/80 p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">Substrate completeness pipeline</h2>
          <p className="mt-1 text-sm text-stone-600">
            Bounded visible incompleteness — not execution analytics. Click a stage to debug omissions.
          </p>
          <p className="mt-1 text-xs text-stone-500">
            {stages.length} stages
            {missingRetrieval ? " · retrieval stage missing from API — refresh after deploy" : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <StatusBadge tone={toneForState(ledger.substrate_state)}>{ledger.substrate_state}</StatusBadge>
          <StatusBadge tone={ledger.substrate_replay_posture === "stable" ? "ok" : "warn"}>
            replay {ledger.substrate_replay_posture}
          </StatusBadge>
        </div>
      </div>
      <div className="mt-4 -mx-1 overflow-x-auto pb-2">
        <div className="flex min-w-min items-stretch gap-2 px-1">
          {stages.map((stage, i) => (
            <div key={stage.stage_id} className="flex items-center gap-2">
              <StageCard stage={stage} />
              {i < stages.length - 1 && (
                <span className="shrink-0 text-stone-400" aria-hidden>
                  →
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
      {chain.length > 0 && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
          <h3 className="text-sm font-semibold text-amber-950">Degradation propagation</h3>
          <ul className="mt-2 space-y-1 text-xs text-amber-900">
            {chain.map((c) => (
              <li key={`${c.from_stage}-${c.to_stage}-${c.explanation_summary}`}>{c.explanation_summary}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
