import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { IdentityPassStaleBadge } from "./cortex/IdentityPassStaleBadge";
import { useDeclaredDomainReadiness } from "./cortex/useDeclaredDomainReadiness";

type Tab = "state" | "runs" | "data";

type NotionPin = {
  database_id: string;
  display_name: string;
  row_count: number;
  is_pinned: boolean;
  is_declared_seed: boolean;
};

const STATUS_LABELS: Record<string, { label: string; className: string; help: string }> = {
  healthy: {
    label: "Working",
    className: "bg-emerald-100 text-emerald-900 ring-emerald-200",
    help: "Declared domains exist with active memberships and no pending backlog.",
  },
  processing: {
    label: "Processing",
    className: "bg-amber-100 text-amber-950 ring-amber-200",
    help: "Pins or backlog detected — run a pass or wait for the scheduler.",
  },
  catching_up: {
    label: "Catching up",
    className: "bg-amber-100 text-amber-950 ring-amber-200",
    help: "Dirty queue has pending work; passes are still draining.",
  },
  needs_setup: {
    label: "Needs setup",
    className: "bg-stone-100 text-stone-800 ring-stone-200",
    help: "Pin Notion work databases in Integrations or connect Linear, then run a pass.",
  },
  failed: {
    label: "Last pass failed",
    className: "bg-red-100 text-red-900 ring-red-200",
    help: "Check Runs tab for errors, then trigger a new pass.",
  },
};

function resolveTab(tabParam: string | null): Tab {
  if (tabParam === "runs") return "runs";
  if (tabParam === "data") return "data";
  return "state";
}

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_LABELS[status] ?? STATUS_LABELS.needs_setup;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${meta.className}`}
      title={meta.help}
    >
      {meta.label}
    </span>
  );
}

function formatPassStats(stats: Record<string, unknown> | undefined): string {
  if (!stats) return "—";
  const parts = [
    `synced ${String(stats.domains_synced ?? 0)}`,
    `refreshed ${String(stats.domains_refreshed ?? 0)}`,
    `processed ${String(stats.processed ?? 0)} dirty`,
  ];
  if (Number(stats.errors ?? 0) > 0) parts.push(`${String(stats.errors)} errors`);
  return parts.join(" · ");
}

function StateTab({ tenantId }: { tenantId: string }) {
  const readinessQ = useDeclaredDomainReadiness();
  const data = readinessQ.data;
  if (!data) return null;
  const last = data.latest_pass_run;
  const pins = (data.notion_pins ?? []) as NotionPin[];
  const status = data.operational_status ?? "needs_setup";

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold text-stone-900">Overall state</h2>
          <StatusBadge status={status} />
        </div>
        <p className="mt-2 text-sm text-stone-600">{(STATUS_LABELS[status] ?? STATUS_LABELS.needs_setup).help}</p>
        <ul className="mt-4 space-y-2 text-sm text-stone-700">
          <li>
            <span className="font-medium text-stone-900">{data.declared_domain_count}</span> declared domains ·{" "}
            <span className="font-medium text-stone-900">{data.active_membership_count}</span> active memberships ·{" "}
            {data.dirty_queue_pending} dirty queue
          </li>
          {last ? (
            <li>
              Last pass <span className="font-medium">{last.status}</span> ({String(last.source_trigger ?? "—")}) ·{" "}
              {formatPassStats(last.stats as Record<string, unknown>)}
            </li>
          ) : (
            <li>No pass runs yet.</li>
          )}
          <li>
            Level 0 = pinned seeds (Notion DB or Linear initiative/project). Level 1 = graph expansion (advisory when
            graph is behind).
          </li>
        </ul>
      </div>

      <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold text-stone-900">Configured seeds (Integrations)</h3>
          <Link
            to={`/admin/tenants/${tenantId}/integrations`}
            className="text-sm text-indigo-700 hover:underline"
          >
            Open Integrations →
          </Link>
        </div>
        {pins.length === 0 ? (
          <p className="mt-2 text-sm text-stone-600">
            No Notion work databases pinned. Pin databases under Integrations → Notion → Declared work containers.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {pins.map((pin) => (
              <li
                key={pin.database_id}
                className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-stone-100 bg-stone-50 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-stone-900">{pin.display_name}</span>
                  <span className="ml-2 text-xs text-stone-500">{pin.row_count.toLocaleString()} rows in canon</span>
                </div>
                <span className="text-xs text-emerald-800">
                  {pin.is_declared_seed ? "declared domain seed" : "pinned · pass pending"}
                </span>
              </li>
            ))}
          </ul>
        )}
        {data.linear_connected ? (
          <p className="mt-3 text-xs text-stone-500">Linear is connected — initiatives/projects can also become seeds.</p>
        ) : null}
      </div>

      <TriggerPassPanel tenantId={tenantId} />
      <RebuildPanel tenantId={tenantId} />
    </div>
  );
}

function RebuildPanel({ tenantId }: { tenantId: string }) {
  return (
    <form
      className="space-y-2 rounded-xl border border-stone-200 bg-stone-50 p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const confirmation = (form.elements.namedItem("rebuild_confirmation") as HTMLInputElement).value;
        await adminFetch(`/admin/tenants/${tenantId}/cortex/declared-domains/actions/rebuild`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation }),
        });
        window.location.reload();
      }}
    >
      <p className="text-sm font-medium text-stone-900">Rebuild declared domains</p>
      <p className="text-xs text-stone-600">
        Type <code className="rounded bg-white px-1">REBUILD DECLARED DOMAINS</code> to clear projection tables and replay
        from canon seeds.
      </p>
      <input
        name="rebuild_confirmation"
        className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
        placeholder="REBUILD DECLARED DOMAINS"
      />
      <button
        type="submit"
        className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50"
      >
        Rebuild
      </button>
    </form>
  );
}

function TriggerPassPanel({ tenantId }: { tenantId: string }) {
  return (
    <form
      className="space-y-2 rounded-xl border border-stone-200 bg-stone-50 p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const confirmation = (form.elements.namedItem("confirmation") as HTMLInputElement).value;
        await adminFetch(`/admin/tenants/${tenantId}/cortex/declared-domains/actions/trigger-pass`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation }),
        });
        window.location.reload();
      }}
    >
      <p className="text-sm font-medium text-stone-900">Run declared domain pass</p>
      <p className="text-xs text-stone-600">
        Type <code className="rounded bg-white px-1">RUN DECLARED DOMAIN PASS</code> to sync seeds and refresh
        memberships.
      </p>
      <input
        name="confirmation"
        className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
        placeholder="RUN DECLARED DOMAIN PASS"
      />
      <button
        type="submit"
        className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
      >
        Trigger pass
      </button>
    </form>
  );
}

function RunsTab({ tenantId }: { tenantId: string }) {
  const runsQ = useQuery({
    queryKey: ["admin-declared-domain-runs", tenantId],
    queryFn: () =>
      adminJson<{ items: Array<Record<string, unknown>> }>(
        `/admin/tenants/${tenantId}/cortex/declared-domains/runs?limit=50`,
      ),
  });
  if (runsQ.isLoading) return <CortexPageSkeleton label="Loading runs" />;
  const items = runsQ.data?.items ?? [];
  return (
    <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
          <tr>
            <th className="px-4 py-2">Started</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Trigger</th>
            <th className="px-4 py-2">Outcome</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={String(row.id)} className="border-t border-stone-100">
              <td className="px-4 py-2 whitespace-nowrap">{String(row.started_at)}</td>
              <td className="px-4 py-2">{String(row.status)}</td>
              <td className="px-4 py-2">{String(row.source_trigger)}</td>
              <td className="px-4 py-2 text-stone-700">
                {formatPassStats(row.stats as Record<string, unknown>)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type MembershipSummary = { total: number; direct: number; graph: number; by_rule?: Record<string, number> };

function MembershipList({
  tenantId,
  memberships,
}: {
  tenantId: string;
  memberships: Array<Record<string, unknown>>;
}) {
  const direct = memberships.filter((m) => m.expansion_level === "direct");
  const graph = memberships.filter((m) => m.expansion_level === "graph");

  const renderGroup = (title: string, items: Array<Record<string, unknown>>) => (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
        {title} ({items.length})
      </p>
      <ul className="mt-1 space-y-1">
        {items.slice(0, 40).map((m) => (
          <li key={String(m.id)} className="rounded bg-stone-50 px-2 py-1.5 text-sm">
            <Link
              className="font-medium text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${String(m.canon_entity_id)}`}
            >
              {String(m.display_label ?? m.canon_entity_id)}
            </Link>
            <span className="text-xs text-stone-500">
              {" "}
              · {String(m.entity_type ?? "entity")}
              {m.resource_type ? ` / ${String(m.resource_type)}` : ""} · {String(m.extractor_rule)}
            </span>
          </li>
        ))}
        {items.length > 40 ? (
          <li className="px-2 py-1 text-xs text-stone-500">… and {items.length - 40} more</li>
        ) : null}
      </ul>
    </div>
  );

  return (
    <div className="mt-3 max-h-[28rem] space-y-4 overflow-y-auto">
      {direct.length > 0 ? renderGroup("Direct (Level 0)", direct) : null}
      {graph.length > 0 ? renderGroup("Graph expanded (Level 1)", graph) : null}
    </div>
  );
}

function DataTab({ tenantId }: { tenantId: string }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const sort = searchParams.get("sort") ?? "mass";
  const domainId = searchParams.get("domain_id");
  const listQ = useQuery({
    queryKey: ["admin-declared-domains", tenantId, sort],
    queryFn: () =>
      adminJson<{ items: Array<Record<string, unknown>> }>(
        `/admin/tenants/${tenantId}/cortex/declared-domains?sort=${sort}&limit=100`,
      ),
  });
  const detailQ = useQuery({
    queryKey: ["admin-declared-domain-detail", tenantId, domainId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/declared-domains/${domainId}`,
      ),
    enabled: Boolean(domainId),
  });

  if (listQ.isLoading) return <CortexPageSkeleton label="Loading domains" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        Each row is one declared domain (seed). Click a domain to inspect its members — Notion rows linked directly, plus
        optional graph-expanded artifacts.
      </p>
      <div className="flex flex-wrap gap-2">
        {(["mass", "activity", "growing", "shrinking", "name"] as const).map((key) => (
          <button
            key={key}
            type="button"
            className={`rounded px-2 py-1 text-sm ${
              sort === key ? "bg-indigo-100 text-indigo-900" : "bg-stone-100 text-stone-700"
            }`}
            onClick={() =>
              setSearchParams((prev) => {
                const p = new URLSearchParams(prev);
                p.set("tab", "data");
                p.set("sort", key);
                return p;
              })
            }
          >
            {key}
          </button>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="px-4 py-2">Domain</th>
                <th className="px-4 py-2">Kind</th>
                <th className="px-4 py-2">Members</th>
                <th className="px-4 py-2">Mass</th>
                <th className="px-4 py-2">7d</th>
              </tr>
            </thead>
            <tbody>
              {(listQ.data?.items ?? []).map((row) => {
                const stats = (row.stats ?? {}) as Record<string, unknown>;
                const summary = (row.membership_summary ?? {}) as MembershipSummary;
                return (
                  <tr
                    key={String(row.id)}
                    className={`cursor-pointer border-t border-stone-100 hover:bg-stone-50 ${
                      domainId === String(row.id) ? "bg-indigo-50" : ""
                    }`}
                    onClick={() =>
                      setSearchParams((prev) => {
                        const p = new URLSearchParams(prev);
                        p.set("tab", "data");
                        p.set("domain_id", String(row.id));
                        return p;
                      })
                    }
                  >
                    <td className="px-4 py-2 font-medium">{String(row.display_name)}</td>
                    <td className="px-4 py-2 text-xs">{String(row.declared_container_kind)}</td>
                    <td className="px-4 py-2">
                      {summary.total ?? row.active_membership_count ?? 0}
                      {summary.direct != null ? (
                        <span className="block text-xs text-stone-500">
                          {summary.direct} direct · {summary.graph} graph
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-2">{String(stats.mass_total ?? 0)}</td>
                    <td className="px-4 py-2">{String(stats.events_7d ?? 0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {domainId && detailQ.data ? (
          <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
            <h3 className="text-lg font-semibold">{String(detailQ.data.display_name)}</h3>
            <p className="text-sm text-stone-600">
              {String(detailQ.data.declared_container_kind)} · seed {String(detailQ.data.seed_resource_type)}
            </p>
            {(() => {
              const summary = (detailQ.data.membership_summary ?? {}) as MembershipSummary;
              const stats = (detailQ.data.stats ?? {}) as Record<string, unknown>;
              return (
                <p className="mt-2 text-sm text-stone-700">
                  <span className="font-medium">{summary.total ?? 0}</span> members ({summary.direct ?? 0} direct Notion
                  / canon rows, {summary.graph ?? 0} via graph) · mass {String(stats.mass_total ?? 0)}
                </p>
              );
            })()}
            <MembershipList
              tenantId={tenantId}
              memberships={(detailQ.data.memberships as Array<Record<string, unknown>>) ?? []}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center rounded-xl border border-dashed border-stone-200 p-8 text-sm text-stone-500">
            Select a domain to inspect members
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminCortexDeclaredDomainsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = resolveTab(searchParams.get("tab"));
  const readinessQ = useDeclaredDomainReadiness();
  const laneStale = Boolean(readinessQ.data?.scheduler?.lane_stale);

  const setTab = (next: Tab) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      if (next === "state") {
        p.delete("tab");
        p.delete("domain_id");
        p.delete("sort");
      } else {
        p.set("tab", next);
      }
      return p;
    });
  };

  if (readinessQ.isLoading) {
    return <CortexPageSkeleton label="Loading declared domains" />;
  }

  const data = readinessQ.data;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-stone-900">Declared Domains</h1>
          {data?.operational_status ? <StatusBadge status={data.operational_status} /> : null}
        </div>
        <p className="mt-1 text-sm text-stone-600">
          Trusted execution containers (Linear initiatives/projects and pinned Notion databases) with deterministic
          membership and momentum.
        </p>
        {data ? (
          <p className="mt-2 text-xs text-stone-500">
            {data.declared_domain_count} domains · {data.active_membership_count} members · {data.dirty_queue_pending}{" "}
            dirty
            {data.graph_behind ? " · graph behind (Level 1 advisory)" : null}
          </p>
        ) : null}
      </header>

      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(
          [
            ["state", "Overall state"],
            ["runs", "Runs"],
            ["data", "Data"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              tab === key
                ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                : "text-stone-700 hover:bg-stone-100"
            }`}
          >
            <span className="inline-flex items-center">
              {label}
              {key === "state" && laneStale ? <IdentityPassStaleBadge /> : null}
            </span>
          </button>
        ))}
      </nav>

      {tab === "state" ? <StateTab tenantId={tenantId} /> : null}
      {tab === "runs" ? <RunsTab tenantId={tenantId} /> : null}
      {tab === "data" ? <DataTab tenantId={tenantId} /> : null}
    </div>
  );
}
