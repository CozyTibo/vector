import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { IdentityPassStaleBadge } from "./cortex/IdentityPassStaleBadge";
import { IdentityRowAvatar } from "./cortex/IdentityRowAvatar";
import { IdentitySchedulerPanel } from "./cortex/IdentitySchedulerPanel";
import { isIdentityPassRunStale } from "./cortex/identityPassRunHealth";
import { useIdentityReadiness } from "./cortex/useIdentityReadiness";
import type {
  IdentityDetail,
  IdentityList,
  IdentityPassRunItem,
  IdentityUnresolvedActors,
} from "./cortexAdminTypes";

function kindQuery(tab: "humans" | "inactive" | "bots" | "unknown"): "human" | "inactive_human" | "bot" | "unknown" {
  if (tab === "humans") return "human";
  if (tab === "inactive") return "inactive_human";
  if (tab === "bots") return "bot";
  return "unknown";
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function formatLinkRule(rule: string): string {
  return rule.replaceAll("_", " ");
}

function evidenceSignals(evidence: Record<string, unknown>): string[] {
  const parts: string[] = [];
  for (const key of ["emails", "handles", "display_names", "provider_ids"] as const) {
    const raw = evidence[key];
    if (!Array.isArray(raw) || raw.length === 0) continue;
    const values = raw.map((v) => String(v)).filter(Boolean);
    if (values.length > 0) parts.push(`${key}: ${values.join(", ")}`);
  }
  return parts;
}

function kindLabel(kind: string): string {
  if (kind === "inactive_human") return "inactive";
  return kind;
}

function IdentityListTab({ kind }: { kind: "human" | "inactive_human" | "bot" | "unknown" }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const q = useQuery({
    queryKey: ["admin-cortex-identities", tenantId, kind],
    queryFn: () =>
      adminJson<IdentityList>(`/admin/tenants/${tenantId}/cortex/identities?kind=${encodeURIComponent(kind)}`),
    enabled: Boolean(tenantId),
  });
  if (q.isPending) return <p className="text-sm text-stone-500">Loading identities…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  const items = q.data?.items ?? [];

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <p className="mb-3 text-xs text-stone-500">
        Expand a row to see linked accounts, match rules, and signal evidence per connector.
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-stone-500">No identities in this bucket.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => {
            const open = expandedIds.has(item.id);
            return (
              <li
                key={item.id}
                className="overflow-hidden rounded-lg border border-stone-200 bg-stone-50/60"
              >
                <button
                  type="button"
                  className="flex w-full items-start gap-3 px-3 py-2.5 text-left hover:bg-stone-100/80"
                  onClick={() => toggleExpanded(item.id)}
                  aria-expanded={open}
                >
                  <span className="shrink-0 pt-1 text-xs font-medium text-indigo-700">
                    {open ? "▼" : "▶"}
                  </span>
                  {kind === "human" && item.avatar_url ? (
                    <IdentityRowAvatar url={item.avatar_url} displayName={item.display_name} />
                  ) : null}
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-stone-900">{item.display_name}</span>
                      <span className="rounded bg-stone-200/80 px-1.5 py-0.5 text-[11px] font-medium text-stone-800">
                        {kindLabel(item.kind)}
                      </span>
                      <span
                        className="rounded bg-indigo-100 px-1.5 py-0.5 text-[11px] font-semibold text-indigo-900"
                        title="Identity resolver version"
                      >
                        v{item.resolver_version}
                      </span>
                    </span>
                    <span className="mt-1 block text-xs text-stone-600">
                      {item.primary_email ?? "no primary email"}
                      <span className="text-stone-400"> · </span>
                      {item.account_count} account{item.account_count === 1 ? "" : "s"}
                      <span className="text-stone-400"> · </span>
                      {item.connectors.join(", ") || "no connectors"}
                      <span className="text-stone-400"> · </span>
                      resolved {formatWhen(item.resolved_at)}
                    </span>
                    <span className="mt-0.5 block truncate font-mono text-[11px] text-stone-400" title={item.id}>
                      {item.id}
                    </span>
                  </span>
                </button>
                {open ? (
                  <IdentityExpandedPanel
                    tenantId={tenantId}
                    identityId={item.id}
                    resolverVersion={item.resolver_version}
                  />
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function IdentityExpandedPanel({
  tenantId,
  identityId,
  resolverVersion,
}: {
  tenantId: string;
  identityId: string;
  resolverVersion: number;
}) {
  const q = useQuery({
    queryKey: ["admin-cortex-identity-detail", tenantId, identityId],
    queryFn: () => adminJson<IdentityDetail>(`/admin/tenants/${tenantId}/cortex/identities/${identityId}`),
    enabled: Boolean(tenantId && identityId),
  });

  if (q.isPending) return <p className="border-t border-stone-200 px-3 py-3 text-sm text-stone-500">Loading accounts…</p>;
  if (q.isError) return <p className="border-t border-stone-200 px-3 py-3 text-sm text-red-700">{(q.error as Error).message}</p>;
  if (!q.data) return null;

  const detail = q.data;
  return (
    <div className="border-t border-stone-200 bg-white px-3 py-3">
      <p className="mb-3 text-xs text-stone-600">
        <span className="font-medium text-stone-700">{detail.accounts.length}</span> linked account
        {detail.accounts.length === 1 ? "" : "s"} · resolver{" "}
        <span className="font-semibold text-indigo-900">v{resolverVersion}</span>
        {detail.resolver_version !== resolverVersion ? (
          <span className="text-amber-700"> (detail reports v{detail.resolver_version})</span>
        ) : null}
      </p>

      {detail.accounts.length === 0 ? (
        <p className="text-sm text-stone-500">No linked accounts.</p>
      ) : (
        <ul className="space-y-3">
          {detail.accounts.map((account) => {
            const signals = evidenceSignals(account.evidence_json);
            return (
              <li
                key={account.identity_account_id}
                className="rounded-lg border border-stone-200 bg-stone-50/80 p-3 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-stone-900">{account.connector}</span>
                  <span className="text-stone-700">{account.display_label}</span>
                  <span className="ml-auto flex flex-wrap items-center gap-2">
                    <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-900">
                      {account.link_tier}
                    </span>
                    <span className="text-stone-600">{formatLinkRule(account.link_rule)}</span>
                    <span className="rounded bg-stone-200/80 px-1.5 py-0.5 text-stone-700">{account.confidence}</span>
                  </span>
                </div>

                <dl className="mt-2 grid gap-1.5 sm:grid-cols-2">
                  <div>
                    <dt className="font-medium text-stone-500">Entity key</dt>
                    <dd className="break-all font-mono text-[11px] text-stone-700">{account.entity_key}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-stone-500">Linked at</dt>
                    <dd className="text-stone-700">{formatWhen(account.linked_at)}</dd>
                  </div>
                  {signals.length > 0 ? (
                    <div className="sm:col-span-2">
                      <dt className="font-medium text-stone-500">Signals</dt>
                      <dd className="mt-0.5 space-y-0.5 text-stone-700">
                        {signals.map((line) => (
                          <div key={line} className="break-words">
                            {line}
                          </div>
                        ))}
                      </dd>
                    </div>
                  ) : null}
                </dl>

                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <Link
                    className="font-medium text-indigo-700 hover:underline"
                    to={`/admin/tenants/${tenantId}/cortex/canon/entities/${account.canon_entity_id}`}
                  >
                    View canon entity
                  </Link>
                  {Object.keys(account.evidence_json).length > 0 ? (
                    <details>
                      <summary className="cursor-pointer text-indigo-700 hover:underline">Evidence JSON</summary>
                      <pre className="mt-1 max-h-48 overflow-auto rounded border border-stone-200 bg-white p-2 font-mono text-[10px] text-stone-700">
                        {JSON.stringify(account.evidence_json, null, 2)}
                      </pre>
                    </details>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
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
    tabParam === "inactive"
      ? "inactive"
      : tabParam === "bots"
        ? "bots"
        : tabParam === "unknown"
          ? "unknown"
          : tabParam === "runs"
            ? "runs"
            : tabParam === "unresolved"
              ? "unresolved"
              : "humans";
  const readinessQ = useIdentityReadiness();
  const passRunStale = isIdentityPassRunStale(readinessQ.data);

  const setTab = (next: "humans" | "inactive" | "bots" | "unknown" | "unresolved" | "runs") => {
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
            identities
            {readinessQ.data.inactive_human_count != null
              ? ` · ${readinessQ.data.inactive_human_count.toLocaleString()} inactive`
              : ""}{" "}
            · {readinessQ.data.unresolved_actor_count.toLocaleString()} unresolved
          </p>
        ) : null}
      </header>

      <IdentitySchedulerPanel />

      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["humans", "Humans"],
            ["inactive", "Inactive humans"],
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
            {key === "runs" && passRunStale ? <IdentityPassStaleBadge /> : null}
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
