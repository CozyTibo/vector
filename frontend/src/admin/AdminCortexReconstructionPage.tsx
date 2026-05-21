import { Link, useParams } from "react-router-dom";

import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";

type ReconstructionSummary = PhaseSummaryPayload & {
  queue_depth?: number;
  failed_jobs?: number;
  job_status_counts?: Record<string, number>;
  last_successful_job?: { job_id: string; completed_at: string | null } | null;
};

export default function AdminCortexReconstructionPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  return (
    <PhasePageShell
      phase="reconstruction"
      title="Reconstruction"
      description="Execution reconstruction jobs (TCRE). Jobs are enqueued by the pipeline — use Overview to re-run from this step."
      summaryContent={(summary) => {
        const s = summary as ReconstructionSummary;
        const counts = s.job_status_counts ?? {};
        return (
          <>
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Queue depth</p>
                <p className="mt-1 text-lg font-semibold">{(s.queue_depth ?? 0).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-red-100 bg-red-50 p-4 shadow-sm">
                <p className="text-xs uppercase text-red-800">Failed jobs</p>
                <p className="mt-1 text-lg font-semibold text-red-950">
                  {(s.failed_jobs ?? 0).toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Running</p>
                <p className="mt-1 text-lg font-semibold">{(counts.running ?? 0).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Completed</p>
                <p className="mt-1 text-lg font-semibold">{(counts.completed ?? 0).toLocaleString()}</p>
              </div>
            </section>
            {s.last_successful_job ? (
              <p className="text-sm text-stone-600">
                Last completed job{" "}
                <Link
                  className="font-mono text-indigo-700 underline"
                  to={`/admin/tenants/${tenantId}/cortex/reconstruction/jobs/${s.last_successful_job.job_id}`}
                >
                  {s.last_successful_job.job_id.slice(0, 8)}…
                </Link>
                {s.last_successful_job.completed_at
                  ? ` · ${new Date(s.last_successful_job.completed_at).toLocaleString()}`
                  : null}
              </p>
            ) : (
              <p className="text-sm text-stone-500">No completed reconstruction jobs yet.</p>
            )}
          </>
        );
      }}
      explorerContent={<PhaseExplorer phase="reconstruction" />}
    />
  );
}
