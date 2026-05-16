import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type Health = {
  tenant_id: string;
  active_tcre_policy_bundle_digest: string;
  active_reasoning_rule_pack_id: string;
  canonical_materialization_count: number;
  queue_depth_proxy: number;
  failed_job_count?: number;
  degraded_chronology_percent?: number;
  degraded_edge_percent?: number;
  avg_reconstruction_duration_seconds?: number | null;
  last_replay_result?: boolean | null;
  last_replay_divergence_at?: string | null;
  last_successful_replay_twin_passed?: boolean | null;
  job_status_counts: Record<string, number>;
  last_successful_job: { job_id: string; completed_at: string | null; summary_json: Record<string, unknown> } | null;
  last_replay_twin_job?: { job_id: string; status: string } | null;
  replay_equivalence_status: string;
  engine_build_ref: string;
  operator_projection_version?: number;
};

export default function AdminCortexReasoningOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const healthQ = useQuery({
    queryKey: ["reasoning-runtime-health", tenantId],
    queryFn: () => adminJson<Health>(`/admin/tenants/${tenantId}/cortex/reasoning/runtime/health`),
  });

  const reconstruct = useMutation({
    mutationFn: (sync: boolean) =>
      adminJson<{ job_id: string; status: string }>(
        `/admin/tenants/${tenantId}/cortex/reasoning/runtime/reconstruct`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ materialization_limit: 50, dry_run: false, run_sync: sync }),
        },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["reasoning-runtime-health", tenantId] });
      void qc.invalidateQueries({ queryKey: ["reasoning-runtime-jobs", tenantId] });
    },
  });

  const h = healthQ.data;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Reconstruction health</h2>
        {healthQ.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {healthQ.error && (
          <p className="mt-2 text-sm text-red-600">{(healthQ.error as Error).message}</p>
        )}
        {h && (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-stone-500">Policy digest</dt>
              <dd className="font-mono text-xs break-all">{h.active_tcre_policy_bundle_digest}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Policy pack</dt>
              <dd>{h.active_reasoning_rule_pack_id}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Canonical materializations</dt>
              <dd>{h.canonical_materialization_count}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Queue depth (queued + running)</dt>
              <dd>{h.queue_depth_proxy}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Replay equivalence</dt>
              <dd>{h.replay_equivalence_status}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Engine</dt>
              <dd className="font-mono text-xs">{h.engine_build_ref}</dd>
            </div>
            {h.degraded_chronology_percent != null && (
              <div>
                <dt className="text-stone-500">Degraded chronology %</dt>
                <dd>{h.degraded_chronology_percent}%</dd>
              </div>
            )}
            {h.avg_reconstruction_duration_seconds != null && (
              <div>
                <dt className="text-stone-500">Avg reconstruction (s)</dt>
                <dd>{h.avg_reconstruction_duration_seconds}</dd>
              </div>
            )}
            {(h.failed_job_count ?? 0) > 0 && (
              <div>
                <dt className="text-stone-500">Failed jobs</dt>
                <dd className="text-red-700">{h.failed_job_count}</dd>
              </div>
            )}
            {h.last_replay_result != null && (
              <div>
                <dt className="text-stone-500">Last replay twin</dt>
                <dd>{h.last_replay_result ? "passed" : "failed"}</dd>
              </div>
            )}
          </dl>
        )}
        {h?.last_successful_job && (
          <p className="mt-4 text-sm text-stone-600">
            Last success:{" "}
            <Link
              className="text-indigo-700 underline"
              to={`/admin/tenants/${tenantId}/cortex/reasoning/jobs/${h.last_successful_job.job_id}`}
            >
              {h.last_successful_job.job_id.slice(0, 8)}…
            </Link>
            {h.last_successful_job.completed_at ? ` at ${h.last_successful_job.completed_at}` : null}
          </p>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Run reconstruction</h2>
        <p className="mt-1 text-sm text-stone-600">
          Bounded slice over canonical materializations (default limit 50). Use sync for immediate
          feedback in dev.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            disabled={reconstruct.isPending}
            onClick={() => reconstruct.mutate(true)}
          >
            Reconstruct (sync)
          </button>
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
            disabled={reconstruct.isPending}
            onClick={() => reconstruct.mutate(false)}
          >
            Enqueue (Celery)
          </button>
        </div>
        {reconstruct.data && (
          <p className="mt-3 text-sm text-green-800">
            Job {reconstruct.data.job_id} — status {reconstruct.data.status}
          </p>
        )}
        {reconstruct.error && (
          <p className="mt-3 text-sm text-red-600">{(reconstruct.error as Error).message}</p>
        )}
      </section>
    </div>
  );
}
