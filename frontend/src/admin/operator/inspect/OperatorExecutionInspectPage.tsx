import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { DeployInfoFooter } from "../DeployInfoFooter";
import { useOperatorExecutionThread } from "../useOperatorInspectChains";

export default function OperatorExecutionInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [draft, setDraft] = useState({
    walk_id: "",
    tcre_job_id: "",
    scope_ref: "",
    replay_identity: "",
  });
  const [submitted, setSubmitted] = useState<Record<string, string>>({});
  const threadQ = useOperatorExecutionThread(submitted, Boolean(Object.values(submitted).some(Boolean)));

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Execution thread</h1>
        <p className="mt-1 text-sm text-stone-600">
          Walk replay lineage, TCRE jobs, and related index entries for a scope.
        </p>
      </header>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <form
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted({ ...draft });
          }}
        >
          {(
            [
              ["walk_id", "Walk id"],
              ["tcre_job_id", "TCRE job id"],
              ["scope_ref", "Scope / island ref"],
              ["replay_identity", "Replay identity"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="block text-sm">
              <span className="text-xs font-medium text-stone-600">{label}</span>
              <input
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 font-mono text-sm"
                value={draft[key]}
                onChange={(e) => setDraft((prev) => ({ ...prev, [key]: e.target.value }))}
              />
            </label>
          ))}
          <div className="flex items-end sm:col-span-2">
            <button
              type="submit"
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Search thread
            </button>
          </div>
        </form>
      </section>

      {threadQ.isPending ? <SectionSkeleton variant="table" /> : null}
      {threadQ.isError ? (
        <p className="text-sm text-red-700">
          {(threadQ.error as Error).message === "search_query_required"
            ? "Provide at least one search field."
            : (threadQ.error as Error).message}
        </p>
      ) : null}
      {threadQ.data ? (
        <>
          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Walk replay lineage</h2>
            {threadQ.data.walk_lineage.length === 0 ? (
              <p className="mt-2 text-sm text-stone-500">No walk hops.</p>
            ) : (
              <ol className="mt-3 space-y-2 border-l-2 border-indigo-200 pl-4">
                {threadQ.data.walk_lineage.map((hop) => (
                  <li key={String(hop.walk_id)} className="text-sm">
                    <span className="font-mono text-xs">{String(hop.walk_id)}</span>
                    <span className="text-stone-500"> · depth {String(hop.depth ?? "—")}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">TCRE jobs</h2>
            {threadQ.data.tcre_jobs.length === 0 ? (
              <p className="mt-2 text-sm text-stone-500">No TCRE jobs.</p>
            ) : (
              <ul className="mt-3 divide-y divide-stone-100">
                {threadQ.data.tcre_jobs.map((job) => (
                  <li key={String(job.job_id)} className="py-3">
                    <p className="text-sm font-medium text-stone-900">
                      {String(job.job_kind)} · {String(job.status)}
                    </p>
                    <p className="mt-1 font-mono text-xs text-stone-600">{String(job.job_id)}</p>
                    <Link
                      to={`/admin/tenants/${tenantId}/cortex/reconstruction/jobs/${String(job.job_id)}`}
                      className="mt-2 inline-block text-xs font-medium text-indigo-700 no-underline hover:underline"
                    >
                      Open reconstruction job →
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Related index entries</h2>
            {threadQ.data.index_entries.length === 0 ? (
              <p className="mt-2 text-sm text-stone-500">No index entries.</p>
            ) : (
              <ul className="mt-3 divide-y divide-stone-100">
                {threadQ.data.index_entries.map((entry) => (
                  <li key={String(entry.entry_id)} className="py-2 text-sm">
                    {String(entry.index_kind)} · {String(entry.index_key)}
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
