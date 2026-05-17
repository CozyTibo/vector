import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type Criterion = {
  criterion_id: string;
  label: string;
  passed: boolean;
  errors: string[];
};

type ChecklistRow = {
  check_id: string;
  label: string;
  detail: string;
  passed: boolean;
};

type ProgramClosure = {
  program_closure_passed: boolean;
  freeze_bundle_id: string;
  retrieval_program_freeze_version: number;
  completion_criteria: Criterion[];
  operator_checklist: ChecklistRow[];
  certification_pack: {
    closure_passed?: boolean;
    whole_file_sha256?: string | null;
    pack_byte_length?: number | null;
  };
  control_plane_surfaces_wired: number;
  control_plane_surfaces_total: number;
};

export default function AdminCortexRetrievalProgramClosurePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const q = useQuery({
    queryKey: ["retrieval-program-closure", tenantId],
    queryFn: () =>
      adminJson<ProgramClosure>(
        `/admin/tenants/${tenantId}/cortex/retrieval/program-closure`,
      ),
  });

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Program closure (FF-P07-5)</h2>
        <p className="mt-1 text-sm text-stone-600">
          Phase 07 completion criteria, operator checklist, and certification pack digest.
        </p>
        {q.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {q.error && <p className="mt-2 text-sm text-red-600">{(q.error as Error).message}</p>}
        {q.data && <ClosureHeader data={q.data} />}
      </section>

      {q.data && (
        <>
          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-stone-800">Completion criteria</h3>
            <ul className="mt-3 space-y-2">
              {q.data.completion_criteria.map((c) => (
                <li
                  key={c.criterion_id}
                  className="flex items-start justify-between gap-3 rounded-md border border-stone-100 px-3 py-2"
                >
                  <div>
                    <span className="font-mono text-xs text-stone-500">{c.criterion_id}</span>
                    <p className="text-sm text-stone-800">{c.label}</p>
                  </div>
                  <StatusBadge tone={c.passed ? "ok" : "warn"}>
                    {c.passed ? "pass" : "fail"}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-stone-800">Operator checklist</h3>
            <ul className="mt-3 space-y-2">
              {q.data.operator_checklist.map((row) => (
                <li
                  key={row.check_id}
                  className="flex items-start justify-between gap-3 rounded-md border border-stone-100 px-3 py-2"
                >
                  <div>
                    <span className="font-mono text-xs text-stone-500">{row.check_id}</span>
                    <p className="text-sm font-medium text-stone-800">{row.label}</p>
                    <p className="text-xs text-stone-600">{row.detail}</p>
                  </div>
                  <StatusBadge tone={row.passed ? "ok" : "warn"}>
                    {row.passed ? "ok" : "pending"}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

function ClosureHeader({ data }: { data: ProgramClosure }) {
  return (
    <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
      <div>
        <dt className="text-stone-500">Program closure</dt>
        <dd>
          <StatusBadge tone={data.program_closure_passed ? "ok" : "warn"}>
            {data.program_closure_passed ? "passed" : "incomplete"}
          </StatusBadge>
        </dd>
      </div>
      <div>
        <dt className="text-stone-500">Freeze bundle</dt>
        <dd className="font-mono text-xs">{data.freeze_bundle_id}</dd>
      </div>
      <div>
        <dt className="text-stone-500">Surfaces wired</dt>
        <dd>
          {data.control_plane_surfaces_wired} / {data.control_plane_surfaces_total}
        </dd>
      </div>
      <div>
        <dt className="text-stone-500">Cert pack</dt>
        <dd>
          {data.certification_pack.closure_passed ? "verified" : "pending"}
          {data.certification_pack.whole_file_sha256 && (
            <p className="mt-1 font-mono text-xs break-all text-stone-600">
              {data.certification_pack.whole_file_sha256}
            </p>
          )}
        </dd>
      </div>
    </dl>
  );
}
