import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { adminJson } from "../lib/adminFetch";

type JobRow = {
  job_id: string;
  status: string;
  synthesis_workload_class: string;
  synthesis_legality_class: string | null;
  created_at: string | null;
};

type JobList = {
  jobs: JobRow[];
};

export default function AdminCortexSynthesisJobsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/synthesis`;

  const { data, isLoading } = useQuery({
    queryKey: ["synthesis-jobs", tenantId],
    queryFn: () => adminJson<JobList>(`/admin/tenants/${tenantId}/cortex/synthesis/jobs`),
  });

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Synthesis jobs</h2>
      <p className="mt-1 text-sm text-stone-600">Job list and debugger (W1 / W4).</p>
      {isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-stone-200 text-stone-500">
            <tr>
              <th className="py-2 pr-4">Job</th>
              <th className="py-2 pr-4">Workload</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Legality</th>
            </tr>
          </thead>
          <tbody>
            {(data?.jobs ?? []).map((j) => (
              <tr key={j.job_id} className="border-b border-stone-100">
                <td className="py-2 pr-4 font-mono text-xs">
                  <Link className="text-violet-700 underline" to={`${base}/jobs/${j.job_id}`}>
                    {j.job_id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="py-2 pr-4">{j.synthesis_workload_class}</td>
                <td className="py-2 pr-4">{j.status}</td>
                <td className="py-2 pr-4 text-xs">{j.synthesis_legality_class ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.jobs.length === 0 && (
          <p className="mt-4 text-sm text-stone-500">No jobs yet.</p>
        )}
      </div>
    </section>
  );
}
