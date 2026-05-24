import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { SectionSkeleton } from "./cortex/SectionSkeleton";

type DebuggerPayload = {
  job_detail: { status: string; synthesis_workload_class: string };
};

export default function AdminCortexSynthesisJobDetailPage() {
  const { tenantId = "", jobId = "" } = useParams<{ tenantId: string; jobId: string }>();
  const backTo = `/admin/tenants/${tenantId}/cortex/inspect/synthesis`;

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["synthesis-job-debugger", tenantId, jobId],
    queryFn: () =>
      adminJson<DebuggerPayload>(
        `/admin/tenants/${tenantId}/cortex/synthesis/jobs/${jobId}/debugger`,
      ),
    enabled: Boolean(jobId),
  });

  if (!jobId) return <p className="text-sm text-stone-500">Missing job id.</p>;

  return (
    <div className="space-y-4">
      <Link className="text-sm text-indigo-700 underline" to={backTo}>
        ← Synthesis inspect
      </Link>
      {isLoading && !data ? (
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <SectionSkeleton variant="cards" />
        </section>
      ) : null}
      {isError ? <p className="text-sm text-red-700">{(error as Error).message}</p> : null}
      {data ? (
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-stone-900">Synthesis job (read-only)</h2>
          <p className="mt-1 text-sm text-stone-600">
            {data.job_detail.synthesis_workload_class} · {data.job_detail.status}
          </p>
          <p className="mt-3 text-xs text-stone-500">
            Re-run synthesis from Overview → Start from step → Synthesis.
          </p>
        </section>
      ) : null}
    </div>
  );
}
