import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type Job = {
  job_id: string;
  status: string;
  job_kind: string;
  created_at: string | null;
  completed_at: string | null;
  summary_json: Record<string, unknown>;
  error_detail: string | null;
};

export default function AdminCortexReasoningJobsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const jobsQ = useQuery({
    queryKey: ["reasoning-runtime-jobs", tenantId],
    queryFn: () =>
      adminJson<Job[]>(`/admin/tenants/${tenantId}/cortex/reasoning/runtime/jobs?limit=50`),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Reconstruction jobs</h2>
      {jobsQ.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      {jobsQ.error && <p className="mt-2 text-sm text-red-600">{(jobsQ.error as Error).message}</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-stone-200 text-stone-500">
            <tr>
              <th className="py-2 pr-4">Job</th>
              <th className="py-2 pr-4">Kind</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Mats</th>
              <th className="py-2 pr-4">Created</th>
            </tr>
          </thead>
          <tbody>
            {(jobsQ.data ?? []).map((j) => (
              <tr key={j.job_id} className="border-b border-stone-100">
                <td className="py-2 pr-4 font-mono text-xs">
                  <Link
                    className="text-indigo-700 underline"
                    to={`/admin/tenants/${tenantId}/cortex/reasoning/jobs/${j.job_id}`}
                  >
                    {j.job_id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="py-2 pr-4">{j.job_kind}</td>
                <td className="py-2 pr-4">{j.status}</td>
                <td className="py-2 pr-4">
                  {String((j.summary_json as { materialization_count?: number }).materialization_count ?? "—")}
                </td>
                <td className="py-2 pr-4 text-xs text-stone-600">{j.created_at ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {jobsQ.data?.length === 0 && (
          <p className="mt-4 text-sm text-stone-500">No jobs yet. Run reconstruction from Overview.</p>
        )}
      </div>
    </section>
  );
}
