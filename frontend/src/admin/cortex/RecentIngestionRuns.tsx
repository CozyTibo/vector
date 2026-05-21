import { Link } from "react-router-dom";

import { titleConnector } from "../cortexAdminTypes";
import type {
  IngestionRunTriggerKind,
  PipelineNextScheduledIngestion,
  PipelineRecentIngestionRun,
} from "./pipelineTypes";
import { StatusBadge } from "../ui/StatusBadge";

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

function triggerLabel(kind: IngestionRunTriggerKind): string {
  if (kind === "scheduled") return "Scheduled";
  if (kind === "replay") return "Replay";
  return "Manual";
}

function statusTone(status: string): "ok" | "warn" | "bad" | "neutral" {
  const s = status.toUpperCase();
  if (s === "COMPLETED") return "ok";
  if (s === "FAILED") return "bad";
  if (s === "RUNNING" || s === "CHECKPOINTING") return "warn";
  return "neutral";
}

type Props = {
  runs: PipelineRecentIngestionRun[];
  tenantId: string;
  nextScheduled?: PipelineNextScheduledIngestion | null;
};

function nextIngestionHeadline(next: PipelineNextScheduledIngestion): string {
  if (next.next_at) {
    return formatExactTime(next.next_at);
  }
  return "—";
}

export function RecentIngestionRuns({ runs, tenantId, nextScheduled }: Props) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-stone-900">Recent ingestion runs</h2>
          <p className="text-sm text-stone-600">Last 10 connector syncs · time, rows written, trigger</p>
        </div>
        <Link
          to={`/admin/tenants/${tenantId}/cortex/ingestion`}
          className="text-sm font-medium text-indigo-700 no-underline hover:underline"
        >
          Ingestion
        </Link>
      </div>
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
      {runs.length === 0 ? (
        <p className="mt-4 text-sm text-stone-500">No ingestion runs recorded for this tenant yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-stone-50 text-left text-stone-700">
              <tr>
                <th className="px-2 py-2">Started</th>
                <th className="px-2 py-2">Connector</th>
                <th className="px-2 py-2">Rows</th>
                <th className="px-2 py-2">Trigger</th>
                <th className="px-2 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id} className="border-t border-stone-100">
                  <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] text-stone-800">
                    {formatExactTime(run.started_at)}
                  </td>
                  <td className="px-2 py-2 font-medium">{titleConnector(run.connector)}</td>
                  <td className="px-2 py-2 tabular-nums">
                    {run.raw_rows_written != null ? run.raw_rows_written.toLocaleString() : "—"}
                  </td>
                  <td className="px-2 py-2">{triggerLabel(run.trigger_kind)}</td>
                  <td className="px-2 py-2">
                    <StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
