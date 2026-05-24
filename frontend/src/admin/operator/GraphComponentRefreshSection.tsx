import { useMutation, useQueryClient } from "@tanstack/react-query";

import { postOperatorGraphSnapshotRefresh } from "./fetchOperator";
import { operatorKeys } from "./operatorKeys";
import { useOperatorGraphSnapshotPolling } from "./useOperatorInspect";
import type { OperatorGraphComponentSnapshot } from "./operatorTypes";

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function statusLabel(status: string | undefined): string {
  switch (status) {
    case "pending":
      return "Queued";
    case "running":
      return "Scanning…";
    case "complete":
      return "Complete";
    case "failed":
      return "Failed";
    default:
      return "Not scanned";
  }
}

function ComponentSummary({ snapshot }: { snapshot: OperatorGraphComponentSnapshot }) {
  if (!snapshot.available) {
    if (snapshot.job_status === "failed" && snapshot.error_detail) {
      return <p className="mt-2 text-sm text-red-700">{snapshot.error_detail}</p>;
    }
    return null;
  }
  return (
    <p className="mt-2 text-sm text-stone-700">
      {snapshot.component_count ?? "—"} connected components · largest{" "}
      {snapshot.largest_component_size ?? "—"} · captured {fmtTime(snapshot.captured_at_utc)}
    </p>
  );
}

type Props = {
  tenantId: string;
  title?: string;
  description?: string;
};

/** Async connected-component refresh + polling (R4). */
export function GraphComponentRefreshSection({
  tenantId,
  title = "Connected components",
  description = "Async scan — never runs on page load. Refresh enqueues a background job.",
}: Props) {
  const queryClient = useQueryClient();
  const snapshotQ = useOperatorGraphSnapshotPolling();
  const component = snapshotQ.data?.component_snapshot;

  const refreshM = useMutation({
    mutationFn: () => postOperatorGraphSnapshotRefresh(tenantId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: operatorKeys.graphSnapshot(tenantId) });
    },
  });

  const busy = component?.job_status === "pending" || component?.job_status === "running";
  const refreshError =
    refreshM.error instanceof Error ? refreshM.error.message : refreshM.isError ? "Refresh failed" : null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
          <p className="mt-1 text-xs text-stone-500">{description}</p>
        </div>
        <button
          type="button"
          disabled={busy || refreshM.isPending}
          onClick={() => refreshM.mutate()}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? statusLabel(component?.job_status) : refreshM.isPending ? "Enqueueing…" : "Refresh components"}
        </button>
      </div>

      {snapshotQ.isError ? (
        <p className="mt-3 text-sm text-red-700">{(snapshotQ.error as Error).message}</p>
      ) : component ? (
        <>
          <p className="mt-3 text-xs text-stone-500">Status: {statusLabel(component.job_status)}</p>
          <ComponentSummary snapshot={component} />
          {component.component_sizes_top_20.length > 0 ? (
            <p className="mt-2 font-mono text-xs text-stone-600">
              Top sizes: {component.component_sizes_top_20.join(", ")}
            </p>
          ) : null}
        </>
      ) : snapshotQ.isPending ? (
        <p className="mt-3 text-sm text-stone-500">Loading snapshot…</p>
      ) : null}

      {refreshError ? <p className="mt-2 text-sm text-red-700">{refreshError}</p> : null}
      {refreshM.data && !refreshM.data.enqueued && refreshM.data.hint === "refresh_already_in_progress" ? (
        <p className="mt-2 text-xs text-amber-800">Refresh already in progress.</p>
      ) : null}
    </section>
  );
}
