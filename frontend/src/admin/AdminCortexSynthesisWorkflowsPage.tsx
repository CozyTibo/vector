import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { adminJson } from "../lib/adminFetch";

type WorkflowStep = {
  label: string;
  spa_route: string;
  external_phase?: string;
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
  remediation_links: { sd_code: string; spa_route: string; hint: string }[];
};

export default function AdminCortexSynthesisWorkflowsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/synthesis`;
  const retrievalBase = `/admin/tenants/${tenantId}/cortex/retrieval`;

  const { data, isLoading } = useQuery({
    queryKey: ["synthesis-workflows", tenantId],
    queryFn: () =>
      adminJson<WorkflowsCatalog>(`/admin/tenants/${tenantId}/cortex/synthesis/workflows`),
  });

  if (isLoading) return <p className="text-sm text-stone-500">Loading workflows…</p>;
  if (!data) return null;

  function stepHref(step: WorkflowStep): string {
    if (step.external_phase === "07" && step.spa_route === "retrieval-query") {
      return `${retrievalBase}/query`;
    }
    return `${base}/${step.spa_route}`;
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Operator workflows</h2>
        <p className="mt-1 text-sm text-stone-600">W1–W4 guided flows with links to debugger surfaces.</p>
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
                  <li key={`${wf.workflow_id}-${step.spa_route}-${step.label}`}>
                    <Link className="text-violet-700 underline" to={stepHref(step)}>
                      {step.label}
                    </Link>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold text-stone-900">Answerability</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {data.answerability_table.map((row) => (
            <li key={row.question}>
              <span className="text-stone-700">{row.question}</span>
              {" → "}
              <Link className="text-violet-700 underline" to={`${base}/${row.spa_route}`}>
                {row.spa_route || "overview"}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
