import { titleConnector } from "../cortexAdminTypes";
import type { CortexConnectorId, CortexRecentRuns } from "../cortexAdminTypes";
import type { IngestionRunTriggerKind, PipelineRecentIngestionRun } from "./pipelineTypes";
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

export function ingestionTriggerKind(
  sourceTrigger: string,
  replayMode: boolean,
): IngestionRunTriggerKind {
  if (replayMode) return "replay";
  const key = (sourceTrigger || "").trim().toLowerCase();
  if (key === "scheduled" || key === "scheduled_lane") return "scheduled";
  if (key === "replay" || key === "manual_admin_replay") return "replay";
  return "manual";
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

export type IngestionRunTableRow = {
  run_id: string;
  connector: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  raw_rows_written: number | null;
  trigger_kind?: IngestionRunTriggerKind;
  source_trigger?: string;
  replay_mode?: boolean;
  sync_mode?: string | null;
  error_summary?: string | null;
};

export function pipelineRunToTableRow(run: PipelineRecentIngestionRun): IngestionRunTableRow {
  return {
    run_id: run.run_id,
    connector: run.connector,
    status: run.status,
    started_at: run.started_at,
    finished_at: run.finished_at,
    raw_rows_written: run.raw_rows_written,
    trigger_kind: run.trigger_kind,
  };
}

export function apiRunToTableRow(
  run: CortexRecentRuns["items"][number],
): IngestionRunTableRow {
  return {
    run_id: String(run.run_id),
    connector: run.connector,
    status: run.status,
    started_at: run.started_at,
    finished_at: run.finished_at,
    raw_rows_written: run.raw_rows_written,
    source_trigger: run.source_trigger,
    replay_mode: run.replay_mode,
    sync_mode: run.sync_mode,
    error_summary: run.error_summary,
  };
}

type Props = {
  runs: IngestionRunTableRow[];
  showFinished?: boolean;
  showSyncMode?: boolean;
  showError?: boolean;
};

export function IngestionRunsTable({
  runs,
  showFinished = false,
  showSyncMode = false,
  showError = false,
}: Props) {
  if (runs.length === 0) {
    return <p className="text-sm text-stone-500">No ingestion runs recorded for this tenant yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead className="bg-stone-50 text-left text-stone-700">
          <tr>
            <th className="px-2 py-2">Started</th>
            {showFinished ? <th className="px-2 py-2">Finished</th> : null}
            <th className="px-2 py-2">Connector</th>
            <th className="px-2 py-2">Rows</th>
            {showSyncMode ? <th className="px-2 py-2">Mode</th> : null}
            <th className="px-2 py-2">Trigger</th>
            <th className="px-2 py-2">Status</th>
            {showError ? <th className="px-2 py-2">Error</th> : null}
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const trigger =
              run.trigger_kind ??
              ingestionTriggerKind(run.source_trigger ?? "", Boolean(run.replay_mode));
            return (
              <tr key={run.run_id} className="border-t border-stone-100">
                <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] text-stone-800">
                  {formatExactTime(run.started_at)}
                </td>
                {showFinished ? (
                  <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] text-stone-600">
                    {run.finished_at ? formatExactTime(run.finished_at) : "—"}
                  </td>
                ) : null}
                <td className="px-2 py-2 font-medium">
                  {titleConnector(run.connector as CortexConnectorId)}
                </td>
                <td className="px-2 py-2 tabular-nums">
                  {run.raw_rows_written != null ? run.raw_rows_written.toLocaleString() : "—"}
                </td>
                {showSyncMode ? (
                  <td className="px-2 py-2 font-mono text-[11px] text-stone-600">
                    {run.sync_mode ?? "—"}
                  </td>
                ) : null}
                <td className="px-2 py-2">{triggerLabel(trigger)}</td>
                <td className="px-2 py-2">
                  <StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge>
                </td>
                {showError ? (
                  <td className="max-w-xs truncate px-2 py-2 text-stone-600" title={run.error_summary ?? ""}>
                    {run.error_summary ?? "—"}
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
