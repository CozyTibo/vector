import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { IdentitySchedulerPanel } from "./cortex/IdentitySchedulerPanel";
import { useIdentityReadiness } from "./cortex/useIdentityReadiness";
import type {
  IdentityDetail,
  IdentityList,
  IdentityPassRunItem,
  IdentityUnresolvedActors,
} from "./cortexAdminTypes";

function kindQuery(tab: "humans" | "bots" | "unknown"): "human" | "bot" | "unknown" {
  if (tab === "humans") return "human";
  if (tab === "bots") return "bot";
  return "unknown";
}

function IdentityListTab({ kind }: { kind: "human" | "bot" | "unknown" }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-identities", tenantId, kind],
    queryFn: () =>
      adminJson<IdentityList>(`/admin/tenants/${tenantId}/cortex/identities?kind=${encodeURIComponent(kind)}`),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading identities…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  const items = q.data?.items ?? [];
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-stone-200 text-left text-stone-500">
            <th className="py-2 pr-3 font-medium">Identity</th>
            <th className="py-2 pr-3 font-medium">Primary email</th>
            <th className="py-2 pr-3 font-medium">Accounts</th>
            <th className="py-2 pr-3 font-medium">Connectors</th>
            <th className="py-2 font-medium">Resolver</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <IdentityRow key={item.id} identityId={item.id} />
          ))}
          {items.length === 0 ? (
            <tr>
              <td colSpan={5} className="py-3 text-stone-500">
                No identities in this bucket.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function IdentityRow({ identityId }: { identityId: string }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-identity-detail-inline", tenantId, identityId],
    queryFn: () => adminJson<IdentityDetail>(`/admin/tenants/${tenantId}/cortex/identities/${identityId}`),
    enabled: Boolean(tenantId && identityId),
  });
  if (!q.data) {
    return (
      <tr className="border-b border-stone-100">
        <td className="py-2 pr-3">Loading…</td>
        <td className="py-2 pr-3">—</td>
        <td className="py-2 pr-3">—</td>
        <td className="py-2 pr-3">—</td>
        <td className="py-2">—</td>
      </tr>
    );
  }
  const connectors = Array.from(new Set(q.data.accounts.map((a) => a.connector))).sort();
  return (
    <tr className="border-b border-stone-100">
      <td className="py-2 pr-3">
        <div className="font-medium text-stone-900">{q.data.display_name}</div>
        <div className="font-mono text-[11px] text-stone-500">{q.data.id}</div>
      </td>
      <td className="py-2 pr-3">{q.data.primary_email ?? "—"}</td>
      <td className="py-2 pr-3">{q.data.accounts.length}</td>
      <td className="py-2 pr-3">{connectors.join(", ") || "—"}</td>
      <td className="py-2">v{q.data.resolver_version}</td>
    </tr>
  );
}

function RunsTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-identities-runs", tenantId],
    queryFn: () => adminJson<{ items: IdentityPassRunItem[] }>(`/admin/tenants/${tenantId}/cortex/identities/runs`),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading runs…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-stone-200 text-left text-stone-500">
            <th className="py-2 pr-3 font-medium">Status</th>
            <th className="py-2 pr-3 font-medium">Trigger</th>
            <th className="py-2 pr-3 font-medium">Started</th>
            <th className="py-2 font-medium">Stats</th>
          </tr>
        </thead>
        <tbody>
          {(q.data?.items ?? []).map((r) => (
            <tr key={r.id} className="border-b border-stone-100">
              <td className="py-2 pr-3">{r.status}</td>
              <td className="py-2 pr-3">{r.source_trigger}</td>
              <td className="py-2 pr-3">{new Date(r.started_at).toLocaleString()}</td>
              <td className="py-2 font-mono text-[11px] text-stone-700">{JSON.stringify(r.stats ?? {})}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UnresolvedTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-identities-unresolved", tenantId],
    queryFn: () =>
      adminJson<IdentityUnresolvedActors>(`/admin/tenants/${tenantId}/cortex/identities/unresolved-actors`),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading unresolved actors…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-stone-200 text-left text-stone-500">
            <th className="py-2 pr-3 font-medium">Connector</th>
            <th className="py-2 pr-3 font-medium">Label</th>
            <th className="py-2 pr-3 font-medium">Entity key</th>
            <th className="py-2 font-medium">Materialized at</th>
          </tr>
        </thead>
        <tbody>
          {(q.data?.items ?? []).map((item) => (
            <tr key={item.canon_entity_id} className="border-b border-stone-100">
              <td className="py-2 pr-3">{item.connector}</td>
              <td className="py-2 pr-3">{item.display_label}</td>
              <td className="py-2 pr-3 font-mono text-[11px]">{item.entity_key}</td>
              <td className="py-2">{new Date(item.materialized_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminCortexIdentitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab =
    tabParam === "bots"
      ? "bots"
      : tabParam === "unknown"
        ? "unknown"
        : tabParam === "runs"
          ? "runs"
          : tabParam === "unresolved"
            ? "unresolved"
            : "humans";
  const readinessQ = useIdentityReadiness();

  const setTab = (next: "humans" | "bots" | "unknown" | "unresolved" | "runs") => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "humans") params.delete("tab");
      else params.set("tab", next);
      return params;
    });
  };

  if (readinessQ.isLoading) return <CortexPageSkeleton label="Loading identities" />;
  if (readinessQ.isError) return <p className="text-sm text-red-700">Failed to load identity readiness.</p>;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Identities</h1>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic account reconciliation across canon actor entities.
        </p>
        {readinessQ.data ? (
          <p className="mt-2 text-xs text-stone-500">
            {readinessQ.data.actor_count.toLocaleString()} actors · {readinessQ.data.identity_count.toLocaleString()}{" "}
            identities · {readinessQ.data.unresolved_actor_count.toLocaleString()} unresolved
          </p>
        ) : null}
      </header>

      <IdentitySchedulerPanel />

      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["humans", "Humans"],
            ["bots", "Bots/services"],
            ["unknown", "Unknown"],
            ["unresolved", "Unresolved actors"],
            ["runs", "Runs"],
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

      {tab === "runs" ? (
        <RunsTab />
      ) : tab === "unresolved" ? (
        <UnresolvedTab />
      ) : (
        <IdentityListTab kind={kindQuery(tab)} />
      )}
    </div>
  );
}

