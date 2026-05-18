import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type DebuggerPayload = {
  job_detail: { status: string; synthesis_workload_class: string };
  remediation_links: { sd_code: string; spa_route: string; hint: string }[];
  retrieval_query_debugger: {
    admin_spa_path: string;
    prefill: Record<string, unknown>;
  };
};

export default function AdminCortexSynthesisJobDebuggerPage() {
  const { tenantId = "", jobId = "" } = useParams<{ tenantId: string; jobId: string }>();
  const qc = useQueryClient();
  const base = `/admin/tenants/${tenantId}/cortex/synthesis`;

  const { data, isLoading } = useQuery({
    queryKey: ["synthesis-job-debugger", tenantId, jobId],
    queryFn: () =>
      adminJson<DebuggerPayload>(
        `/admin/tenants/${tenantId}/cortex/synthesis/jobs/${jobId}/debugger`,
      ),
    enabled: Boolean(jobId),
  });

  const retryMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/synthesis/jobs/${jobId}/retry`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["synthesis-job-debugger", tenantId, jobId] });
      void qc.invalidateQueries({ queryKey: ["synthesis-jobs", tenantId] });
    },
  });

  if (!jobId) return <p className="text-sm text-stone-500">Select a job from the list.</p>;
  if (isLoading) return <p className="text-sm text-stone-500">Loading debugger…</p>;
  if (!data) return null;

  const retrievalPath = data.retrieval_query_debugger.admin_spa_path.replace(
    "{tenant_id}",
    tenantId,
  );

  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link className="text-violet-700 underline" to={`${base}/jobs`}>
          ← Jobs
        </Link>
      </p>
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Job debugger</h2>
        <p className="mt-1 text-sm text-stone-600">
          {data.job_detail.synthesis_workload_class} · {data.job_detail.status}
        </p>
        <button
          type="button"
          className="mt-3 rounded bg-stone-800 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          disabled={retryMut.isPending}
          onClick={() => retryMut.mutate()}
        >
          {retryMut.isPending ? "Retrying…" : "Retry job (W4)"}
        </button>
        {retryMut.error && (
          <p className="mt-2 text-sm text-red-700">{(retryMut.error as Error).message}</p>
        )}
      </section>
      {data.remediation_links.length > 0 && (
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h3 className="font-semibold text-stone-900">SD remediation</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {data.remediation_links.map((l) => (
              <li key={l.sd_code}>
                <span className="font-mono text-xs">{l.sd_code}</span> — {l.hint}{" "}
                <Link className="text-violet-700 underline" to={`${base}/${l.spa_route}`}>
                  {l.spa_route}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold text-stone-900">Phase 07 cross-link</h3>
        <Link className="text-violet-700 underline" to={retrievalPath}>
          Open retrieval query debugger
        </Link>
        <pre className="mt-2 max-h-32 overflow-auto rounded border border-stone-200 bg-stone-50 p-2 text-xs">
          {JSON.stringify(data.retrieval_query_debugger.prefill, null, 2)}
        </pre>
      </section>
    </div>
  );
}
