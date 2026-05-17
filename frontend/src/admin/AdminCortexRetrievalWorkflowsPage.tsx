import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { adminJson } from "../lib/adminFetch";

type WorkflowStep = {
  label: string;
  spa_route: string;
  phase?: string;
  workload_class?: string;
};

type Workflow = {
  workflow_id: string;
  title: string;
  steps: string;
  dangerous?: boolean;
  spa_steps: WorkflowStep[];
};

type WorkflowsCatalog = {
  workflows: Workflow[];
  answerability_table: { question: string; spa_route: string }[];
  remediation_links: { retrieval_omission_class: string; spa_route: string; hint: string }[];
  spa_route_registry: { surface_id: string; label: string; spa_route: string; wired: boolean }[];
};

export default function AdminCortexRetrievalWorkflowsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/retrieval`;

  const { data, isLoading } = useQuery({
    queryKey: ["retrieval-workflows", tenantId],
    queryFn: () =>
      adminJson<WorkflowsCatalog>(`/admin/tenants/${tenantId}/cortex/retrieval/workflows`),
  });

  if (isLoading) return <p className="text-sm text-stone-500">Loading workflows…</p>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Operator workflows</h2>
        <p className="mt-1 text-sm text-stone-600">W1–W3 guided flows with links to debugger surfaces.</p>
        <div className="mt-4 space-y-4">
          {data.workflows.map((wf) => (
            <div key={wf.workflow_id} className="rounded border border-stone-200 p-3">
              <h3 className="font-medium text-stone-900">
                {wf.workflow_id}: {wf.title}
                {wf.dangerous && (
                  <span className="ml-2 text-xs font-normal text-amber-800">(dangerous)</span>
                )}
              </h3>
              <p className="mt-1 text-xs text-stone-500">{wf.steps}</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                {wf.spa_steps.map((step) => (
                  <li key={`${wf.workflow_id}-${step.spa_route}`}>
                    <Link className="text-violet-700 underline" to={`${base}/${step.spa_route}`}>
                      {step.label}
                    </Link>
                    {step.phase && <span className="text-stone-500"> — {step.phase}</span>}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold text-stone-900">Answerability (no SQL)</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {data.answerability_table.map((row) => (
            <li key={row.question}>
              <span className="text-stone-700">{row.question}</span>
              {" → "}
              <Link className="text-violet-700 underline" to={`${base}/${row.spa_route}`}>
                {row.spa_route}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
