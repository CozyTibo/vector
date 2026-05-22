import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { StatusBadge } from "../ui/StatusBadge";
import { CortexPageSkeleton } from "./CortexPageSkeleton";
import type { OperatorPhase, PhaseStatus, PipelineOverview } from "./pipelineTypes";
import { usePipelineOverview } from "./usePipelineOverview";

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

type PhaseTab = "summary" | "explorer" | "runs";

type Props = {
  phase: OperatorPhase;
  title: string;
  description: string;
  summaryContent: (summary: PhaseSummaryPayload) => React.ReactNode;
  explorerContent: React.ReactNode;
  runsContent?: React.ReactNode;
};

function resolvePhaseTab(tabParam: string | null, hasRunsTab: boolean): PhaseTab {
  if (hasRunsTab && tabParam === "runs") return "runs";
  if (tabParam === "explorer") return "explorer";
  return "summary";
}

function phaseRowFromOverview(overview: PipelineOverview | undefined, phase: OperatorPhase) {
  return overview?.phases.find((p) => p.phase === phase);
}

export function PhasePageShell({
  phase,
  title,
  description,
  summaryContent,
  explorerContent,
  runsContent,
}: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = resolvePhaseTab(searchParams.get("tab"), Boolean(runsContent));

  const setTab = (next: PhaseTab) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "summary") params.delete("tab");
      else params.set("tab", next);
      if (next !== "runs") {
        params.delete("page");
        params.delete("connector");
      }
      return params;
    });
  };
  const overviewPath = `/admin/tenants/${tenantId}/cortex/overview`;

  const overviewQ = usePipelineOverview();
  const headerRow = phaseRowFromOverview(overviewQ.data, phase);

  const summaryQ = useQuery({
    queryKey: ["admin-cortex-phase-summary", tenantId, phase],
    queryFn: () =>
      adminJson<PhaseSummaryPayload & Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/pipeline/phases/${phase}/summary`,
      ),
    enabled: Boolean(tenantId) && tab === "summary",
    staleTime: 45_000,
    placeholderData: headerRow
      ? {
          phase,
          status: headerRow.status,
          processed_count: headerRow.processed_count ?? null,
          backlog_count: headerRow.backlog_count ?? null,
          last_success_at: headerRow.last_success_at ?? null,
          blockers: headerRow.blockers ?? [],
        }
      : undefined,
  });

  const headerStatus = headerRow?.status ?? summaryQ.data?.status;
  const headerPending = overviewQ.isPending && !headerRow;
  const headerError = overviewQ.isError && !headerRow;

  const s = summaryQ.data;
  const summaryLoading = tab === "summary" && summaryQ.isFetching && !summaryQ.isFetched;

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Pipeline phase</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">{title}</h1>
        <p className="mt-1 text-sm text-stone-600">{description}</p>
        {headerPending ? (
          <p className="mt-3 text-sm text-stone-500">Loading phase status…</p>
        ) : headerError ? (
          <p className="mt-3 text-sm text-red-700">{(overviewQ.error as Error).message}</p>
        ) : headerStatus ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge tone={statusTone(headerStatus)}>
              {headerRow?.status_label ?? headerStatus}
            </StatusBadge>
            {(headerRow?.processed_count ?? s?.processed_count) != null ? (
              <span className="text-stone-600">
                Processed {(headerRow?.processed_count ?? s?.processed_count)!.toLocaleString()}
              </span>
            ) : null}
            {(headerRow?.backlog_count ?? s?.backlog_count) != null &&
            (headerRow?.backlog_count ?? s?.backlog_count)! > 0 ? (
              <span className="text-amber-800">
                Backlog {(headerRow?.backlog_count ?? s?.backlog_count)!.toLocaleString()}
              </span>
            ) : null}
            {(headerRow?.last_success_at ?? s?.last_success_at) ? (
              <span className="text-stone-500">
                Last success{" "}
                {new Date(headerRow?.last_success_at ?? s?.last_success_at!).toLocaleString()}
              </span>
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
          onClick={() => setTab("summary")}
        >
          Summary
        </button>
        {runsContent ? (
          <button
            type="button"
            className={[
              "rounded-md border px-3 py-1.5 text-sm font-medium",
              tab === "runs"
                ? "border-indigo-300 bg-indigo-100 text-indigo-900"
                : "border-stone-200 bg-white text-stone-700",
            ].join(" ")}
            onClick={() => setTab("runs")}
          >
            Runs
          </button>
        ) : null}
        <button
          type="button"
          className={[
            "rounded-md border px-3 py-1.5 text-sm font-medium",
            tab === "explorer"
              ? "border-indigo-300 bg-indigo-100 text-indigo-900"
              : "border-stone-200 bg-white text-stone-700",
          ].join(" ")}
          onClick={() => setTab("explorer")}
        >
          Explorer
        </button>
      </nav>

      {tab === "runs" && runsContent ? (
        runsContent
      ) : tab === "summary" ? (
        <div className="space-y-4">
          {summaryQ.isError ? (
            <p className="text-sm text-red-700">{(summaryQ.error as Error).message}</p>
          ) : null}
          {summaryLoading ? (
            <CortexPageSkeleton label="Loading phase details…" />
          ) : (
            <>
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
            </>
          )}
        </div>
      ) : (
        explorerContent
      )}
    </div>
  );
}
