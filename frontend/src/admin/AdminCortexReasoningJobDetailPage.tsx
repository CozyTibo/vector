import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type ChronologyExplanation = {
  materialization_id: string;
  canonical_object_kind: string | null;
  occurred_at: string | null;
  observed_at: string | null;
  replay_safe_ordering: string;
  chronology_legality_class: string;
  chronology_projection_rule_id: string;
  explanation_summary: string;
  skew_detected: boolean;
  late_arrival: boolean;
};

type EdgeExplanation = {
  tcre_causal_edge_id: string;
  from_materialization_id: string;
  to_materialization_id: string;
  derivation_rule_label: string;
  causal_legality_class: string;
  explanation_summary: string;
};

type TimelineStep = {
  step_index: number;
  source_materialization_id: string;
  target_materialization_id: string;
  edge_explanation_summary: string;
  source_chronology_legality_class: string;
  target_chronology_legality_class: string;
};

type OctsBinding = {
  binding_legality_class: string;
  walk_hash: string;
  traversal_receipt_digest: string;
  ingestion_replay_identity: string;
  continuity_proof_ref: string | null;
  traversal_epoch: string | null;
  octs_walk_id: string | null;
};

type OperatorView = {
  job_id: string;
  status: string;
  job_kind: string;
  octs_binding: OctsBinding | null;
  reconstruction_summary: Record<string, unknown>;
  chronology_explanations: ChronologyExplanation[];
  edge_explanations: EdgeExplanation[];
  chain_timeline: { steps: TimelineStep[]; causal_chain_id: string | null };
  degradation_explanations: { explanation_summary: string; scope: string }[];
  replay_diff: {
    identical: boolean;
    chronology_divergence: unknown[];
    edge_divergence: unknown[];
    chain_divergence: boolean;
    digest_mismatch: boolean;
  } | null;
};

function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-stone-100">
      <button
        type="button"
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-stone-800"
        onClick={() => setOpen((o) => !o)}
      >
        {title}
        <span className="text-stone-400">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="border-t border-stone-100 px-3 py-2">{children}</div>}
    </div>
  );
}

export default function AdminCortexReasoningJobDetailPage() {
  const { tenantId = "", jobId = "" } = useParams<{ tenantId: string; jobId: string }>();
  const qc = useQueryClient();

  const viewQ = useQuery({
    queryKey: ["reasoning-operator-view", tenantId, jobId],
    queryFn: () =>
      adminJson<OperatorView>(
        `/admin/tenants/${tenantId}/cortex/reasoning/runtime/jobs/${jobId}/operator-view`,
      ),
    enabled: Boolean(jobId),
  });

  const twin = useMutation({
    mutationFn: () =>
      adminJson<{
        replay_equivalence_passed: boolean;
        twin_job_id: string;
        replay_diff?: OperatorView["replay_diff"];
      }>(
        `/admin/tenants/${tenantId}/cortex/reasoning/runtime/jobs/${jobId}/replay-twin`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["reasoning-operator-view", tenantId, jobId] });
      void qc.invalidateQueries({ queryKey: ["reasoning-runtime-health", tenantId] });
    },
  });

  const v = viewQ.data;
  const summary = v?.reconstruction_summary;
  const [edgeKindFilter, setEdgeKindFilter] = useState("");
  const [chronClassFilter, setChronClassFilter] = useState("");
  const [degradationOnly, setDegradationOnly] = useState(false);

  const filteredChronology =
    v?.chronology_explanations.filter((c) => {
      if (chronClassFilter && c.chronology_legality_class !== chronClassFilter) return false;
      if (degradationOnly && c.chronology_legality_class !== "chronology_degraded") return false;
      return true;
    }) ?? [];
  const filteredEdges =
    v?.edge_explanations.filter((e) => {
      if (edgeKindFilter && !e.derivation_rule_label.includes(edgeKindFilter)) return false;
      if (degradationOnly && e.causal_legality_class === "causal_replay_equivalent") return false;
      return true;
    }) ?? [];

  return (
    <div className="space-y-6">
      {viewQ.isLoading && <p className="text-sm text-stone-500">Loading operator view…</p>}
      {viewQ.error && <p className="text-sm text-red-600">{(viewQ.error as Error).message}</p>}
      {v && (
        <>
          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-stone-900">Job {v.job_id.slice(0, 8)}…</h2>
            <p className="mt-1 text-sm text-stone-600">
              {v.status} · {v.job_kind}
            </p>
            {summary && (
              <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <dt className="text-stone-500">Materializations</dt>
                  <dd>{String(summary.materializations_processed)}</dd>
                </div>
                <div>
                  <dt className="text-stone-500">Chronology strict / degraded</dt>
                  <dd>
                    {String(summary.chronology_strict_count)} / {String(summary.chronology_degraded_count)}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500">Policy pack</dt>
                  <dd className="font-mono text-xs">{String(summary.policy_pack_id)}</dd>
                </div>
                <div>
                  <dt className="text-stone-500">Engine</dt>
                  <dd className="font-mono text-xs">{String(summary.engine_build_ref)}</dd>
                </div>
                <div>
                  <dt className="text-stone-500">Duration (s)</dt>
                  <dd>
                    {summary.runtime_duration_seconds != null
                      ? String(summary.runtime_duration_seconds)
                      : "—"}
                  </dd>
                </div>
              </dl>
            )}
            {v.status === "completed" && v.job_kind === "reconstruct" && (
              <button
                type="button"
                className="mt-4 rounded-md border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-50"
                disabled={twin.isPending}
                onClick={() => twin.mutate()}
              >
                Run replay twin compare
              </button>
            )}
            {twin.data && (
              <div className="mt-4 space-y-2 text-sm">
                <p className={twin.data.replay_equivalence_passed ? "text-green-800" : "text-red-700"}>
                  Replay equivalence: {twin.data.replay_equivalence_passed ? "PASSED" : "FAILED"}
                </p>
                {twin.data.replay_diff && !twin.data.replay_diff.identical && (
                  <ul className="list-inside list-disc text-stone-700">
                    {twin.data.replay_diff.chronology_divergence.length > 0 && (
                      <li>
                        Chronology divergence: {twin.data.replay_diff.chronology_divergence.length}{" "}
                        row(s)
                      </li>
                    )}
                    {twin.data.replay_diff.edge_divergence.length > 0 && (
                      <li>Edge divergence: {twin.data.replay_diff.edge_divergence.length} edge(s)</li>
                    )}
                    {twin.data.replay_diff.chain_divergence && <li>Chain divergence</li>}
                    {twin.data.replay_diff.digest_mismatch && <li>Aggregate digest mismatch</li>}
                  </ul>
                )}
              </div>
            )}
            {v.replay_diff && !v.replay_diff.identical && (
              <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                Stored replay diff: chronology {v.replay_diff.chronology_divergence.length}, edges{" "}
                {v.replay_diff.edge_divergence.length}
                {v.replay_diff.chain_divergence ? ", chain mismatch" : ""}
              </div>
            )}
          </section>

          {v.octs_binding && (
            <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5 shadow-sm">
              <h3 className="font-semibold text-indigo-950">OCTS traversal binding</h3>
              <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-indigo-700">Binding legality</dt>
                  <dd className="font-mono">{v.octs_binding.binding_legality_class}</dd>
                </div>
                <div>
                  <dt className="text-indigo-700">Walk hash</dt>
                  <dd className="break-all font-mono text-xs">{v.octs_binding.walk_hash}</dd>
                </div>
                <div>
                  <dt className="text-indigo-700">Traversal receipt digest</dt>
                  <dd className="break-all font-mono text-xs">
                    {v.octs_binding.traversal_receipt_digest || "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-indigo-700">Replay identity</dt>
                  <dd className="break-all font-mono text-xs">
                    {v.octs_binding.ingestion_replay_identity || "—"}
                  </dd>
                </div>
                {v.octs_binding.continuity_proof_ref && (
                  <div>
                    <dt className="text-indigo-700">Continuity proof ref</dt>
                    <dd className="font-mono text-xs">{v.octs_binding.continuity_proof_ref}</dd>
                  </div>
                )}
              </dl>
            </section>
          )}

          <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-stone-800">Explorer filters</h3>
            <div className="mt-2 flex flex-wrap gap-3 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={degradationOnly}
                  onChange={(e) => setDegradationOnly(e.target.checked)}
                />
                Degraded only
              </label>
              <select
                className="rounded border border-stone-300 px-2 py-1"
                value={chronClassFilter}
                onChange={(e) => setChronClassFilter(e.target.value)}
              >
                <option value="">All chronology classes</option>
                <option value="chronology_strict">chronology_strict</option>
                <option value="chronology_degraded">chronology_degraded</option>
                <option value="chronology_partial">chronology_partial</option>
              </select>
              <input
                className="rounded border border-stone-300 px-2 py-1"
                placeholder="Edge rule label filter"
                value={edgeKindFilter}
                onChange={(e) => setEdgeKindFilter(e.target.value)}
              />
            </div>
          </section>

          {v.degradation_explanations.length > 0 && (
            <section className="rounded-xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm">
              <h3 className="font-semibold text-amber-950">Why degraded?</h3>
              <ul className="mt-2 space-y-2 text-sm text-amber-900">
                {v.degradation_explanations.map((d, i) => (
                  <li key={`${d.scope}-${i}`}>{d.explanation_summary}</li>
                ))}
              </ul>
            </section>
          )}

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-stone-900">
              Chain timeline ({v.chain_timeline.steps?.length ?? 0} steps)
            </h3>
            {v.chain_timeline.causal_chain_id && (
              <p className="mt-1 font-mono text-xs text-stone-500">
                chain: {v.chain_timeline.causal_chain_id.slice(0, 20)}…
              </p>
            )}
            <ol className="mt-4 space-y-3 border-l-2 border-stone-200 pl-4">
              {v.chain_timeline.steps?.map((step) => (
                <li key={step.step_index} className="relative text-sm">
                  <span className="absolute -left-[1.35rem] top-1 h-2 w-2 rounded-full bg-indigo-500" />
                  <p className="font-mono text-xs text-stone-500">
                    {step.source_materialization_id.slice(0, 8)}… →{" "}
                    {step.target_materialization_id.slice(0, 8)}…
                  </p>
                  <p className="mt-1 text-stone-800">{step.edge_explanation_summary}</p>
                  <p className="mt-1 text-xs text-stone-500">
                    chronology: {step.source_chronology_legality_class} →{" "}
                    {step.target_chronology_legality_class}
                  </p>
                </li>
              ))}
            </ol>
          </section>

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-stone-900">
              Chronology ({filteredChronology.length}/{v.chronology_explanations.length})
            </h3>
            <ul className="mt-3 space-y-2">
              {filteredChronology.map((c) => (
                <li key={c.materialization_id} className="rounded-lg border border-stone-100 text-sm">
                  <Collapsible
                    title={`${c.canonical_object_kind ?? "unknown"} · ${c.chronology_legality_class} · ${c.chronology_projection_rule_id}`}
                  >
                    <p className="text-stone-700">{c.explanation_summary}</p>
                    <dl className="mt-2 grid gap-1 text-xs text-stone-600 sm:grid-cols-2">
                      <div>replay_safe_ordering: {c.replay_safe_ordering}</div>
                      <div>skew: {String(c.skew_detected)} · late: {String(c.late_arrival)}</div>
                      {c.occurred_at && <div>occurred_at: {c.occurred_at}</div>}
                      {c.observed_at && <div>observed_at: {c.observed_at}</div>}
                    </dl>
                  </Collapsible>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-stone-900">
              Causal edges ({filteredEdges.length}/{v.edge_explanations.length})
            </h3>
            <ul className="mt-3 space-y-2">
              {filteredEdges.map((e) => (
                <li key={e.tcre_causal_edge_id} className="rounded-lg border border-stone-100 text-sm">
                  <Collapsible title={`${e.derivation_rule_label} · ${e.causal_legality_class}`}>
                    <p className="text-stone-700">{e.explanation_summary}</p>
                    <p className="mt-1 font-mono text-xs text-stone-500">
                      {e.from_materialization_id.slice(0, 8)}… → {e.to_materialization_id.slice(0, 8)}…
                    </p>
                  </Collapsible>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
