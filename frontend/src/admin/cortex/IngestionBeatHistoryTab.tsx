import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CortexSchedulerBeats } from "../cortexAdminTypes";
import { titleConnector } from "../cortexAdminTypes";
import { SectionSkeleton } from "./SectionSkeleton";

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function statusBadge(status: string): string {
  if (status === "completed") return "bg-emerald-100 text-emerald-900";
  if (status === "failed") return "bg-red-100 text-red-900";
  if (status === "running") return "bg-amber-100 text-amber-900";
  if (status === "queued" || status === "not_enqueued") return "bg-stone-100 text-stone-700";
  return "bg-stone-100 text-stone-800";
}

export function IngestionBeatHistoryTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const beatsQ = useQuery({
    queryKey: ["admin-cortex-ingestion-beats", tenantId],
    queryFn: () =>
      adminJson<CortexSchedulerBeats>(
        `/admin/tenants/${tenantId}/cortex/ingestion/scheduler-beats?limit=20`,
      ),
    enabled: Boolean(tenantId),
    refetchInterval: 30_000,
  });

  const items = beatsQ.data?.items ?? [];

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-stone-900">Ingestion Beat history</h2>
        <p className="text-sm text-stone-600">
          Last 20 Celery Beat ticks (ingestion-only, every ~2 minutes) with a per-connector debrief
          of what was enqueued and raw rows added.
        </p>
      </div>

      {beatsQ.isPending && !beatsQ.data ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : beatsQ.isError ? (
        <p className="mt-4 text-sm text-red-700">{(beatsQ.error as Error).message}</p>
      ) : items.length === 0 ? (
        <p className="mt-4 text-sm text-stone-600">
          No Beat ticks yet for this workspace. Ensure celery-beat is running and this tenant is
          routed for live sync.
        </p>
      ) : (
        <ul className="mt-4 space-y-4">
          {items.map((beat) => (
            <li
              key={beat.tick_id}
              className="rounded-lg border border-stone-200 bg-stone-50/50 p-4"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-stone-900">
                    Beat · {formatWhen(beat.started_at)}
                  </p>
                  <p className="text-xs text-stone-500">
                    tick {beat.tick_id.slice(0, 8)}… · outcome {beat.outcome}
                    {beat.skip_reason ? ` · ${beat.skip_reason}` : ""}
                  </p>
                </div>
                <p className="text-xs text-stone-600">
                  enqueued {beat.tenant_enqueued_count} connector(s) · interval{" "}
                  {beat.beat_interval_seconds}s
                </p>
              </div>

              {beat.connectors.length === 0 ? (
                <p className="mt-2 text-xs text-stone-500">No connector work for this tenant.</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-stone-200 text-stone-500">
                        <th className="py-1 pr-3 font-medium">Connector</th>
                        <th className="py-1 pr-3 font-medium">Status</th>
                        <th className="py-1 pr-3 font-medium">Added</th>
                        <th className="py-1 pr-3 font-medium">By resource</th>
                        <th className="py-1 font-medium">Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {beat.connectors.map((row) => (
                        <tr key={row.connector} className="border-b border-stone-100">
                          <td className="py-2 pr-3 font-medium text-stone-800">
                            {titleConnector(row.connector)}
                            {!row.enqueued ? (
                              <span className="ml-1 text-stone-400">(not enqueued)</span>
                            ) : null}
                          </td>
                          <td className="py-2 pr-3">
                            <span
                              className={[
                                "rounded px-1.5 py-0.5 font-medium",
                                statusBadge(row.status),
                              ].join(" ")}
                            >
                              {row.status}
                            </span>
                          </td>
                          <td className="py-2 pr-3 text-stone-700">
                            {row.records_written == null
                              ? "—"
                              : row.records_written.toLocaleString()}
                          </td>
                          <td className="py-2 pr-3 text-stone-600">
                            {row.resource_breakdown.length === 0
                              ? "—"
                              : row.resource_breakdown
                                  .map((r) => `${r.resource_type}: ${r.count}`)
                                  .join(", ")}
                          </td>
                          <td className="py-2 max-w-xs truncate text-red-700">
                            {row.error_summary ?? "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
