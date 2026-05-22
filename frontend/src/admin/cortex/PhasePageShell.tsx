import { Link, useParams, useSearchParams } from "react-router-dom";

import { StatusBadge } from "../ui/StatusBadge";
import type { OperatorPhase, PhaseStatus, PipelineOverview } from "./pipelineTypes";
import { SectionSkeleton } from "./SectionSkeleton";
import { usePhaseSummaryDetail } from "./usePhaseSummaryDetail";
import { usePipelineOverviewPhases } from "./usePipelineOverview";

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
  /** When true, summary tab renders immediately and children fetch their own data. */
  summaryLoadsOwnData?: boolean;
  summaryContent: (summary: PhaseSummaryPayload & Record<string, unknown>) => React.ReactNode;
  explorerContent: React.ReactNode;
  runsContent?: React.ReactNode;
};

function resolvePhaseTab(tabParam: string | null, hasRunsTab: boolean): PhaseTab {
  if (hasRunsTab && tabParam === "runs") return "runs";
  if (tabParam === "explorer") return "explorer";
  return "summary";
}

function phaseRowFromPhases(
  phases: PipelineOverview["phases"] | undefined,
  phase: OperatorPhase,
) {
  return phases?.find((p) => p.phase === phase);
}

function coreFromPhaseRow(
  phase: OperatorPhase,
  row: PipelineOverview["phases"][number],
): PhaseSummaryPayload {
  return {
    phase,
    status: row.status,
    processed_count: row.processed_count ?? null,
    backlog_count: row.backlog_count ?? null,
    last_success_at: row.last_success_at ?? null,
    blockers: row.blockers ?? [],
  };
}

export function PhasePageShell({
  phase,
  title,
  description,
  summaryLoadsOwnData = false,
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

  const phasesQ = usePipelineOverviewPhases();
  const headerRow = phaseRowFromPhases(phasesQ.data?.phases, phase);
  const detailQ = usePhaseSummaryDetail(phase, tab === "summary" && !summaryLoadsOwnData);

  const core = headerRow ? coreFromPhaseRow(phase, headerRow) : null;
  const detail = detailQ.data;
  const merged =
    core && detail
      ? ({
          ...core,
          ...Object.fromEntries(
            Object.entries(detail).filter(
              ([k]) => !["surface_kind", "phase", "tenant_id"].includes(k),
            ),
          ),
        } as PhaseSummaryPayload & Record<string, unknown>)
      : core;

  const headerStatus = headerRow?.status;
  const headerPending = phasesQ.isPending && !headerRow;
  const headerError = phasesQ.isError && !headerRow;
  const detailLoading = tab === "summary" && detailQ.isPending && !detailQ.data;
  const blockers = core?.blockers ?? [];

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Pipeline phase</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">{title}</h1>
        <p className="mt-1 text-sm text-stone-600">{description}</p>
        {headerPending ? (
          <div className="mt-4 h-6 w-48 animate-pulse rounded bg-stone-200" aria-hidden />
        ) : headerError ? (
          <p className="mt-3 text-sm text-red-700">{(phasesQ.error as Error).message}</p>
        ) : headerStatus ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge tone={statusTone(headerStatus)}>
              {headerRow?.status_label ?? headerStatus}
            </StatusBadge>
            {headerRow?.processed_count != null ? (
              <span className="text-stone-600">
                Processed {headerRow.processed_count.toLocaleString()}
              </span>
            ) : null}
            {headerRow?.backlog_count != null && headerRow.backlog_count > 0 ? (
              <span className="text-amber-800">
                Backlog {headerRow.backlog_count.toLocaleString()}
              </span>
            ) : null}
            {headerRow?.last_success_at ? (
              <span className="text-stone-500">
                Last success {new Date(headerRow.last_success_at).toLocaleString()}
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
          {detailQ.isError ? (
            <p className="text-sm text-red-700">{(detailQ.error as Error).message}</p>
          ) : null}
          {blockers.length > 0 ? (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-amber-950">Blockers</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
                {blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </section>
          ) : null}
          {summaryLoadsOwnData ? (
            summaryContent({ ...(core ?? { phase, status: "waiting", processed_count: null, backlog_count: null, last_success_at: null, blockers: [] }) })
          ) : (
            <>
              {detailLoading ? <SectionSkeleton variant="cards" /> : null}
              {merged && !detailLoading ? summaryContent(merged) : null}
            </>
          )}
        </div>
      ) : (
        explorerContent
      )}
    </div>
  );
}
