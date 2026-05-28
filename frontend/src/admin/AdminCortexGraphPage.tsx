import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { GraphSchedulerPanel } from "./cortex/GraphSchedulerPanel";
import { useGraphReadiness } from "./cortex/useGraphReadiness";
import type {
  GraphPassRuns,
  GraphRelationshipList,
  GraphStats,
  GraphUnresolvedList,
} from "./cortexAdminTypes";

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function LinksTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams] = useSearchParams();
  const entityFilter = searchParams.get("entity_id") ?? "";
  const q = useQuery({
    queryKey: ["admin-cortex-graph-relationships", tenantId, entityFilter],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "50", offset: "0" });
      if (entityFilter) params.set("entity_id", entityFilter);
      return adminJson<GraphRelationshipList>(
        `/admin/tenants/${tenantId}/cortex/graph/relationships?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading links…</p>;
  if (q.isError) return <p className="text-sm text-red-700">Failed to load links.</p>;
  const items = q.data?.items ?? [];
  if (items.length === 0) {
    return <p className="text-sm text-stone-500">No active execution links yet.</p>;
  }
  return (
    <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
      {items.map((row) => (
        <li key={row.id} className="space-y-1 p-4 text-sm">
          <p className="font-medium text-stone-900">
            <span className="text-indigo-800">{row.relationship_kind_label}</span>
            <span className="text-stone-400"> · {row.confidence}</span>
          </p>
          <p className="text-stone-700">
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.from.entity_id}`}
            >
              {row.from.display_label ?? row.from.entity_id}
            </Link>
            <span className="mx-2 text-stone-400">→</span>
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.to.entity_id}`}
            >
              {row.to.display_label ?? row.to.entity_id}
            </Link>
          </p>
          <p className="font-mono text-xs text-stone-500">
            {row.extractor_rule} · {formatWhen(row.observed_at)}
          </p>
        </li>
      ))}
    </ul>
  );
}

function OverviewTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-graph-stats", tenantId],
    queryFn: () => adminJson<GraphStats>(`/admin/tenants/${tenantId}/cortex/graph/stats`),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading stats…</p>;
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-stone-200 text-stone-600">
          <th className="py-2 pr-4">Kind</th>
          <th className="py-2">Count</th>
        </tr>
      </thead>
      <tbody>
        {(q.data?.by_kind ?? []).map((row) => (
          <tr key={row.relationship_kind} className="border-b border-stone-50">
            <td className="py-2 pr-4">{row.relationship_kind_label}</td>
            <td className="py-2">{row.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function UnresolvedTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-graph-unresolved", tenantId],
    queryFn: () =>
      adminJson<GraphUnresolvedList>(
        `/admin/tenants/${tenantId}/cortex/graph/unresolved?limit=50`,
      ),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading unresolved…</p>;
  const items = q.data?.items ?? [];
  if (items.length === 0) {
    return <p className="text-sm text-stone-500">No unresolved reference tokens.</p>;
  }
  return (
    <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white text-sm">
      {items.map((row) => (
        <li key={row.id} className="space-y-1 p-4">
          <p className="font-mono text-stone-800">{row.reference_text}</p>
          <p className="text-stone-600">
            {row.reference_kind} · {row.extractor_rule}
          </p>
          {row.source_entity ? (
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.source_entity.entity_id}`}
            >
              {row.source_entity.display_label}
            </Link>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function RunsTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-graph-runs", tenantId],
    queryFn: () =>
      adminJson<GraphPassRuns>(`/admin/tenants/${tenantId}/cortex/graph/runs?limit=30`),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading runs…</p>;
  return (
    <ul className="space-y-2 text-sm">
      {(q.data?.items ?? []).map((run) => (
        <li key={run.id} className="rounded border border-stone-100 p-3">
          <span className="font-medium">{run.status}</span>
          <span className="text-stone-500"> · {run.source_trigger}</span>
          <span className="text-stone-500"> · {formatWhen(run.started_at)}</span>
          {run.stats ? (
            <pre className="mt-1 max-h-24 overflow-auto text-xs text-stone-600">
              {JSON.stringify(run.stats, null, 2)}
            </pre>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export default function AdminCortexGraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab =
    tabParam === "overview"
      ? "overview"
      : tabParam === "runs"
        ? "runs"
        : tabParam === "unresolved"
          ? "unresolved"
          : "links";
  const readinessQ = useGraphReadiness();

  const setTab = (next: "links" | "overview" | "runs" | "unresolved") => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      if (next === "links") p.delete("tab");
      else p.set("tab", next);
      return p;
    });
  };

  if (readinessQ.isLoading) {
    return <CortexPageSkeleton label="Loading graph projection" />;
  }

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Links</h1>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic execution relationships projected from canon and provider evidence.
        </p>
      </header>
      <GraphSchedulerPanel />
      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["links", "Links"],
            ["overview", "Overview"],
            ["runs", "Pass runs"],
            ["unresolved", "Unresolved"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={[
              "rounded-md px-3 py-1.5 text-sm font-medium",
              tab === key
                ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                : "text-stone-700 hover:bg-stone-100",
            ].join(" ")}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "links" ? <LinksTab /> : null}
      {tab === "overview" ? <OverviewTab /> : null}
      {tab === "runs" ? <RunsTab /> : null}
      {tab === "unresolved" ? <UnresolvedTab /> : null}
    </div>
  );
}
