import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../cortex/SectionSkeleton";
import { DeployInfoFooter } from "./DeployInfoFooter";
import { operatorQueueTabs, useOperatorQueues } from "./useOperatorQueues";
import type { OperatorQueueItem, OperatorQueueTab } from "./operatorTypes";

function fmtTime(iso: unknown): string {
  if (!iso || typeof iso !== "string") return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function itemTitle(item: OperatorQueueItem): string {
  const kind = String(item.kind ?? "item");
  if (kind === "synthesis_job") return `Synthesis ${String(item.id ?? "")}`;
  if (kind === "tcre_job") return `TCRE ${String(item.id ?? "")}`;
  if (kind === "deferral") return `Deferral raw ${String(item.raw_record_id ?? "")}`;
  if (kind === "ingestion_run") return `Ingestion ${String(item.id ?? "")}`;
  return kind;
}

function itemDetail(item: OperatorQueueItem, tab: OperatorQueueTab): string {
  if (tab === "synthesis_failed") {
    return [item.intent, item.workload_class, item.error_detail].filter(Boolean).join(" · ");
  }
  if (tab === "tcre_queued") {
    return [item.job_kind, JSON.stringify(item.scope_summary ?? {})].filter(Boolean).join(" · ");
  }
  if (tab === "deferrals") {
    return [item.connector, item.resource_type, item.deferral_reason, item.missing_parent_ref]
      .filter(Boolean)
      .join(" · ");
  }
  if (tab === "ingestion_failed") {
    return [item.connector, item.error_summary].filter(Boolean).join(" · ");
  }
  return "";
}

function itemTime(item: OperatorQueueItem, tab: OperatorQueueTab): string {
  if (tab === "deferrals") return fmtTime(item.retry_ready_at);
  if (tab === "ingestion_failed") return fmtTime(item.started_at);
  return fmtTime(item.completed_at ?? item.created_at ?? item.started_at);
}

export default function OperatorQueuesPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const queuesQ = useOperatorQueues(50);
  const tabs = operatorQueueTabs();

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  if (queuesQ.isError) {
    return <p className="text-sm text-red-700">{(queuesQ.error as Error).message}</p>;
  }

  const data = queuesQ.data;
  const loading = queuesQ.isPending && !data;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Queues</h1>
        <p className="mt-1 text-sm text-stone-600">
          Actionable backlog: failed synthesis, queued TCRE, retry-ready deferrals, failed ingestion.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2">
        {tabs.map((t) => {
          const count = data?.counts[t.key] ?? 0;
          const active = queuesQ.tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => queuesQ.setTab(t.key)}
              className={[
                "rounded-md px-3 py-1.5 text-sm font-medium",
                active
                  ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                  : "bg-white text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50",
              ].join(" ")}
            >
              {t.label} ({count})
            </button>
          );
        })}
      </nav>

      {loading ? (
        <SectionSkeleton variant="table" />
      ) : data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-600">
            {data.total} item{data.total === 1 ? "" : "s"} · showing {data.offset + 1}–
            {Math.min(data.offset + data.items.length, data.total)}
          </p>
          {data.items.length === 0 ? (
            <p className="mt-4 text-sm text-stone-500">No items in this queue.</p>
          ) : (
            <ul className="mt-4 divide-y divide-stone-100">
              {data.items.map((item, idx) => (
                <li key={`${item.kind}-${String(item.id ?? item.raw_record_id ?? idx)}`} className="py-3">
                  <p className="text-sm font-medium text-stone-900">{itemTitle(item)}</p>
                  <p className="mt-1 text-xs text-stone-600">{itemDetail(item, queuesQ.tab)}</p>
                  <p className="mt-1 text-xs text-stone-400">{itemTime(item, queuesQ.tab)}</p>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={queuesQ.offset <= 0}
              onClick={() => queuesQ.setOffset(queuesQ.offset - queuesQ.limit)}
              className="rounded-md border border-stone-300 px-3 py-1 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={queuesQ.offset + queuesQ.limit >= data.total}
              onClick={() => queuesQ.setOffset(queuesQ.offset + queuesQ.limit)}
              className="rounded-md border border-stone-300 px-3 py-1 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
          <p className="mt-3 text-xs text-stone-500">
            Deep links:{" "}
            <Link to={`/admin/tenants/${tenantId}/cortex/synthesis`} className="text-indigo-700">
              synthesis
            </Link>
            {" · "}
            <Link to={`/admin/tenants/${tenantId}/cortex/reconstruction`} className="text-indigo-700">
              reconstruction
            </Link>
            {" · "}
            <Link to={`/admin/tenants/${tenantId}/cortex/canonical`} className="text-indigo-700">
              canonical
            </Link>
            {" · "}
            <Link to={`/admin/tenants/${tenantId}/cortex/ingestion`} className="text-indigo-700">
              ingestion
            </Link>
          </p>
        </section>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
