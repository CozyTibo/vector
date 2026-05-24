import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { DeployInfoFooter } from "../DeployInfoFooter";
import { useOperatorSynthesisJobs } from "../useOperatorInspectChains";

function fmtTime(iso: unknown): string {
  if (!iso || typeof iso !== "string") return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function OperatorSynthesisInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [status, setStatus] = useState("all");
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState({ status: "all", q: "" });
  const jobsQ = useOperatorSynthesisJobs(submitted, true);

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Synthesis inspect</h1>
        <p className="mt-1 text-sm text-stone-600">
          Search synthesis jobs and open the existing debugger for grounding evidence.
        </p>
      </header>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted({ status, q });
          }}
        >
          <label className="block text-sm">
            <span className="text-xs font-medium text-stone-600">Status</span>
            <select
              className="mt-1 rounded-md border border-stone-300 px-3 py-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="all">All</option>
              <option value="failed">Failed</option>
              <option value="complete">Complete</option>
              <option value="running">Running</option>
              <option value="queued">Queued</option>
            </select>
          </label>
          <label className="block min-w-[200px] flex-1 text-sm">
            <span className="text-xs font-medium text-stone-600">Search</span>
            <input
              className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
              placeholder="Job id, intent, workload, error"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
          <button
            type="submit"
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Search jobs
          </button>
        </form>
      </section>

      {jobsQ.isPending && !jobsQ.data ? (
        <SectionSkeleton variant="table" />
      ) : jobsQ.isError ? (
        <p className="text-sm text-red-700">{(jobsQ.error as Error).message}</p>
      ) : jobsQ.data ? (
        <>
          {jobsQ.data.recent_artifacts.length > 0 ? (
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-stone-900">Recent published artifacts</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {jobsQ.data.recent_artifacts.map((artifact) => (
                  <li key={String(artifact.artifact_id ?? artifact.id)}>
                    <span className="font-medium">{String(artifact.artifact_kind ?? "artifact")}</span>
                    <span className="text-stone-500"> · job {String(artifact.job_id ?? "—")}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-stone-600">
              {jobsQ.data.total} job{jobsQ.data.total === 1 ? "" : "s"}
            </p>
            {jobsQ.data.jobs.length === 0 ? (
              <p className="mt-3 text-sm text-stone-500">No jobs match this filter.</p>
            ) : (
              <ul className="mt-4 divide-y divide-stone-100">
                {jobsQ.data.jobs.map((job) => (
                  <li key={String(job.job_id)} className="py-3">
                    <p className="text-sm font-medium text-stone-900">
                      {String(job.status)} · {String(job.synthesis_workload_class)}
                    </p>
                    <p className="mt-1 text-xs text-stone-600">
                      {String(job.synthesis_intent)} · {fmtTime(job.created_at)}
                    </p>
                    {job.error_detail ? (
                      <p className="mt-1 text-xs text-red-700">{String(job.error_detail)}</p>
                    ) : null}
                    <Link
                      to={`/admin/tenants/${tenantId}/cortex/synthesis/jobs/${String(job.job_id)}`}
                      className="mt-2 inline-block text-xs font-medium text-indigo-700 no-underline hover:underline"
                    >
                      Open job debugger →
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
