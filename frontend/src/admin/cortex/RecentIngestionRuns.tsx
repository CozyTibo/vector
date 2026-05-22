import { Link } from "react-router-dom";

import type {
  PipelineNextScheduledIngestion,
  PipelineRecentIngestionRun,
} from "./pipelineTypes";
import { IngestionRunsTable, pipelineRunToTableRow } from "./IngestionRunsTable";
import { SectionSkeleton } from "./SectionSkeleton";

function formatExactTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

type Props = {
  runs: PipelineRecentIngestionRun[];
  tenantId: string;
  nextScheduled?: PipelineNextScheduledIngestion | null;
  loading?: boolean;
  error?: string | null;
};

function nextIngestionHeadline(next: PipelineNextScheduledIngestion): string {
  if (next.next_at) {
    return formatExactTime(next.next_at);
  }
  return "—";
}

export function RecentIngestionRuns({ runs, tenantId, nextScheduled, loading, error }: Props) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-stone-900">Recent ingestion runs</h2>
          <p className="text-sm text-stone-600">Last 10 connector syncs · time, rows written, trigger</p>
        </div>
        <Link
          to={`/admin/tenants/${tenantId}/cortex/ingestion?tab=runs`}
          className="text-sm font-medium text-indigo-700 no-underline hover:underline"
        >
          See all runs
        </Link>
      </div>
      {loading ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : error ? (
        <p className="mt-4 text-sm text-red-700">{error}</p>
      ) : (
        <>
          {nextScheduled ? (
            <div
              className={`mt-4 rounded-lg border px-4 py-3 ${
                nextScheduled.status === "paused" || nextScheduled.status === "disabled"
                  ? "border-amber-200 bg-amber-50"
                  : "border-stone-200 bg-stone-50"
              }`}
            >
              <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
                Next scheduled ingestion
              </p>
              <p className="mt-1 text-sm font-semibold text-stone-900">
                {nextScheduled.next_at ? (
                  <>
                    <span className="font-mono">{nextIngestionHeadline(nextScheduled)}</span>
                    {nextScheduled.status === "eligible_now" ? (
                      <span className="ml-2 font-normal text-stone-600">
                        {new Date(nextScheduled.next_at).getTime() > Date.now() + 60_000
                          ? "(eligible · next beat)"
                          : "(eligible now)"}
                      </span>
                    ) : nextScheduled.status === "waiting_cooldown" ? (
                      <span className="ml-2 font-normal text-stone-600">(next scheduled enqueue)</span>
                    ) : null}
                  </>
                ) : (
                  <span className="font-normal text-stone-700">Not scheduled</span>
                )}
              </p>
              <p className="mt-1 text-sm text-stone-600">{nextScheduled.summary}</p>
            </div>
          ) : null}
          <div className="mt-4">
            <IngestionRunsTable runs={runs.map(pipelineRunToTableRow)} />
          </div>
        </>
      )}
    </section>
  );
}
