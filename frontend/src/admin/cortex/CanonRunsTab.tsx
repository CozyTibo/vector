import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { StatusBadge } from "../ui/StatusBadge";
import type { CanonPassRunItem } from "../cortexAdminTypes";
import { SectionSkeleton } from "./SectionSkeleton";

const PAGE_SIZE = 50;

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

function triggerLabel(sourceTrigger: string): string {
  const key = (sourceTrigger || "").trim().toLowerCase();
  if (key === "scheduled") return "Scheduled";
  if (key === "manual_admin") return "Manual";
  return sourceTrigger || "—";
}

function statusTone(status: string): "ok" | "warn" | "bad" | "neutral" {
  const s = status.toUpperCase();
  if (s === "COMPLETED") return "ok";
  if (s === "FAILED") return "bad";
  if (s === "RUNNING") return "warn";
  return "neutral";
}

function statNum(stats: Record<string, unknown> | null, key: string): number | null {
  if (!stats || !(key in stats)) return null;
  const v = stats[key];
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

type PassRunsResponse = {
  items: CanonPassRunItem[];
  total_count: number;
  offset: number;
  limit: number;
};

export function CanonRunsTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(0, Number.parseInt(searchParams.get("page") ?? "0", 10) || 0);
  const offset = page * PAGE_SIZE;

  const runsQ = useQuery({
    queryKey: ["admin-cortex-canon-passes", tenantId, page],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      return adminJson<PassRunsResponse>(
        `/admin/tenants/${tenantId}/cortex/canon/recent-passes?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const data = runsQ.data;
  const total = data?.total_count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  const setPage = (nextPage: number) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", "runs");
      if (nextPage <= 0) next.delete("page");
      else next.set("page", String(nextPage));
      return next;
    });
  };

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-stone-900">Canon passes</h2>
        <p className="text-sm text-stone-600">Materialization pass history · newest first</p>
      </div>

      {runsQ.isPending && !data ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : runsQ.isError ? (
        <p className="mt-4 text-sm text-red-700">{(runsQ.error as Error).message}</p>
      ) : (
        <>
          <p className="mt-3 text-xs text-stone-500">
            {total === 0
              ? "No canon passes recorded for this workspace yet."
              : `Showing ${from.toLocaleString()}–${to.toLocaleString()} of ${total.toLocaleString()} pass(es)`}
          </p>
          <CanonRunsTable runs={data?.items ?? []} />
          {total > PAGE_SIZE ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
                disabled={page <= 0}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <span className="text-xs text-stone-600">
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
                disabled={page + 1 >= pageCount}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

function CanonRunsTable({ runs }: { runs: CanonPassRunItem[] }) {
  if (runs.length === 0) {
    return <p className="mt-4 text-sm text-stone-500">No canon passes recorded for this workspace yet.</p>;
  }

  return (
    <div className="mt-3 overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead className="bg-stone-50 text-left text-stone-700">
          <tr>
            <th className="px-2 py-2">Started</th>
            <th className="px-2 py-2">Finished</th>
            <th className="px-2 py-2">Trigger</th>
            <th className="px-2 py-2">Status</th>
            <th className="px-2 py-2">Scanned</th>
            <th className="px-2 py-2">Materialized</th>
            <th className="px-2 py-2">Skipped</th>
            <th className="px-2 py-2">Errors</th>
            <th className="px-2 py-2">Error</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-t border-stone-100">
              <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] text-stone-800">
                {formatExactTime(run.started_at)}
              </td>
              <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] text-stone-600">
                {run.finished_at ? formatExactTime(run.finished_at) : "—"}
              </td>
              <td className="px-2 py-2">{triggerLabel(run.source_trigger)}</td>
              <td className="px-2 py-2">
                <StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge>
              </td>
              <td className="px-2 py-2 tabular-nums">{fmtStat(run.stats, "scanned")}</td>
              <td className="px-2 py-2 tabular-nums">{fmtStat(run.stats, "materialized")}</td>
              <td className="px-2 py-2 tabular-nums">{fmtStat(run.stats, "skipped")}</td>
              <td className="px-2 py-2 tabular-nums">{fmtStat(run.stats, "errors")}</td>
              <td
                className="max-w-xs truncate px-2 py-2 text-stone-600"
                title={run.error_summary ?? ""}
              >
                {run.error_summary ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function fmtStat(stats: Record<string, unknown> | null, key: string): string {
  const n = statNum(stats, key);
  return n != null ? n.toLocaleString() : "—";
}
