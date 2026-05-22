import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { SectionSkeleton } from "./cortex/SectionSkeleton";

type OperatorView = {
  job_id: string;
  status: string;
  job_kind: string;
  reconstruction_summary: Record<string, unknown>;
  replay_diff: {
    identical: boolean;
    chronology_divergence: unknown[];
    edge_divergence: unknown[];
  } | null;
};

export default function AdminCortexReasoningJobDetailPage() {
  const { tenantId = "", jobId = "" } = useParams<{ tenantId: string; jobId: string }>();

  const viewQ = useQuery({
    queryKey: ["reasoning-operator-view", tenantId, jobId],
    queryFn: () =>
      adminJson<OperatorView>(
        `/admin/tenants/${tenantId}/cortex/reasoning/runtime/jobs/${jobId}/operator-view`,
      ),
    enabled: Boolean(jobId),
  });

  const v = viewQ.data;
  const base = `/admin/tenants/${tenantId}/cortex/reconstruction`;

  return (
    <div className="space-y-4">
      <Link className="text-sm text-indigo-700 underline" to={base}>
        ← Reconstruction
      </Link>
      {viewQ.isPending && !v ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="h-6 w-48 animate-pulse rounded bg-stone-200" />
          <div className="mt-4">
            <SectionSkeleton variant="cards" />
          </div>
        </section>
      ) : null}
      {viewQ.isError ? <p className="text-sm text-red-700">{(viewQ.error as Error).message}</p> : null}
      {v ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h1 className="text-lg font-semibold text-stone-900">Job {v.job_id.slice(0, 8)}…</h1>
          <p className="mt-1 text-sm text-stone-600">
            Status {v.status} · kind {v.job_kind}
          </p>
          {v.replay_diff && !v.replay_diff.identical ? (
            <p className="mt-2 text-sm text-amber-800">
              Stored diff: chronology {v.replay_diff.chronology_divergence.length}, edges{" "}
              {v.replay_diff.edge_divergence.length}
            </p>
          ) : null}
          <pre className="mt-4 max-h-[32rem] overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-[11px]">
            {JSON.stringify(v.reconstruction_summary ?? {}, null, 2)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}
