import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { StatusBadge } from "../ui/StatusBadge";
import type { OperatorPhase, PhaseStatus } from "./pipelineTypes";

export type PhaseSummaryPayload = {
  phase: string;
  status: PhaseStatus;
  processed_count: number | null;
  backlog_count: number | null;
  last_success_at: string | null;
  blockers: string[];
};

function statusTone(status: PhaseStatus): "ok" | "warn" | "bad" | "neutral" {
  if (status === "healthy") return "ok";
  if (status === "running") return "neutral";
  if (status === "waiting") return "warn";
  if (status === "blocked") return "bad";
  return "warn";
}

type Props = {
  phase: OperatorPhase;
  title: string;
  description: string;
  summaryContent: (summary: PhaseSummaryPayload) => React.ReactNode;
  explorerContent: React.ReactNode;
};

export function PhasePageShell({ phase, title, description, summaryContent, explorerContent }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "explorer" ? "explorer" : "summary";
  const overviewPath = `/admin/tenants/${tenantId}/cortex/overview`;

  const summaryQ = useQuery({
    queryKey: ["admin-cortex-phase-summary", tenantId, phase],
    queryFn: () =>
      adminJson<PhaseSummaryPayload & Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/pipeline/phases/${phase}/summary`,
      ),
    enabled: Boolean(tenantId),
  });

  const s = summaryQ.data;

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Pipeline phase</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">{title}</h1>
        <p className="mt-1 text-sm text-stone-600">{description}</p>
        {summaryQ.isPending ? (
          <p className="mt-3 text-sm text-stone-500">Loading phase summary…</p>
        ) : summaryQ.isError ? (
          <p className="mt-3 text-sm text-red-700">{(summaryQ.error as Error).message}</p>
        ) : s ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge tone={statusTone(s.status)}>{s.status}</StatusBadge>
            {s.processed_count != null ? (
              <span className="text-stone-600">Processed {s.processed_count.toLocaleString()}</span>
            ) : null}
            {s.backlog_count != null && s.backlog_count > 0 ? (
              <span className="text-amber-800">Backlog {s.backlog_count.toLocaleString()}</span>
            ) : null}
            {s.last_success_at ? (
              <span className="text-stone-500">Last success {new Date(s.last_success_at).toLocaleString()}</span>
            ) : null}
            <Link className="font-medium text-indigo-700 underline" to={overviewPath}>
              Pipeline overview
            </Link>
          </div>
        ) : null}
      </header>

      <nav className="flex gap-2">
        <button
          type="button"
          className={[
            "rounded-md border px-3 py-1.5 text-sm font-medium",
            tab === "summary"
              ? "border-indigo-300 bg-indigo-100 text-indigo-900"
              : "border-stone-200 bg-white text-stone-700",
          ].join(" ")}
          onClick={() => setSearchParams({ tab: "summary" })}
        >
          Summary
        </button>
        <button
          type="button"
          className={[
            "rounded-md border px-3 py-1.5 text-sm font-medium",
            tab === "explorer"
              ? "border-indigo-300 bg-indigo-100 text-indigo-900"
              : "border-stone-200 bg-white text-stone-700",
          ].join(" ")}
          onClick={() => setSearchParams({ tab: "explorer" })}
        >
          Explorer
        </button>
      </nav>

      {tab === "summary" ? (
        <div className="space-y-4">
          {s && s.blockers.length > 0 ? (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-amber-950">Blockers</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
                {s.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </section>
          ) : null}
          {s ? summaryContent(s) : null}
        </div>
      ) : (
        explorerContent
      )}
    </div>
  );
}
