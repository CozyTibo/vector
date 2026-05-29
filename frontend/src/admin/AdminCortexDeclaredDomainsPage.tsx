import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { adminFetch, adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";
import { IdentityPassStaleBadge } from "./cortex/IdentityPassStaleBadge";
import { useDeclaredDomainReadiness } from "./cortex/useDeclaredDomainReadiness";

type Tab = "state" | "runs" | "data";

function resolveTab(tabParam: string | null): Tab {
  if (tabParam === "runs") return "runs";
  if (tabParam === "data") return "data";
  return "state";
}

function StateTab({ tenantId }: { tenantId: string }) {
  const readinessQ = useDeclaredDomainReadiness();
  const data = readinessQ.data;
  if (!data) return null;
  const last = data.latest_pass_run;
  return (
    <div className="space-y-4 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Overall state</h2>
      <ul className="space-y-2 text-sm text-stone-700">
        <li>
          {data.declared_domain_count} declared domains · {data.active_membership_count} active
          memberships · {data.dirty_queue_pending} dirty queue
        </li>
        <li>
          Level 0 always available when Linear initiatives/projects are materialized.
          {data.level1_advisory
            ? " Graph lane is behind — cross-tool expansion may be incomplete."
            : " Graph expansion is current."}
        </li>
        {last ? (
          <li>
            Last pass {last.status} · processed{" "}
            {typeof last.stats?.processed === "number" ? last.stats.processed : 0} dirty rows ·
            refreshed{" "}
            {typeof last.stats?.domains_refreshed === "number" ? last.stats.domains_refreshed : 0}{" "}
            domains
          </li>
        ) : (
          <li>No pass runs yet.</li>
        )}
      </ul>
      <TriggerPassPanel tenantId={tenantId} />
    </div>
  );
}

function TriggerPassPanel({ tenantId }: { tenantId: string }) {
  return (
    <form
      className="mt-4 space-y-2 rounded border border-stone-200 bg-stone-50 p-4"
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
        Type <code className="rounded bg-white px-1">RUN DECLARED DOMAIN PASS</code> to enqueue a
        drain pass.
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
            <th className="px-4 py-2">Stats</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={String(row.id)} className="border-t border-stone-100">
              <td className="px-4 py-2">{String(row.started_at)}</td>
              <td className="px-4 py-2">{String(row.status)}</td>
              <td className="px-4 py-2">{String(row.source_trigger)}</td>
              <td className="px-4 py-2 font-mono text-xs">{JSON.stringify(row.stats ?? {})}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
                <th className="px-4 py-2">Mass</th>
                <th className="px-4 py-2">7d</th>
                <th className="px-4 py-2">Δ</th>
              </tr>
            </thead>
            <tbody>
              {(listQ.data?.items ?? []).map((row) => {
                const stats = (row.stats ?? {}) as Record<string, unknown>;
                return (
                  <tr
                    key={String(row.id)}
                    className="cursor-pointer border-t border-stone-100 hover:bg-stone-50"
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
                    <td className="px-4 py-2">{String(row.declared_container_kind)}</td>
                    <td className="px-4 py-2">{String(stats.mass_total ?? 0)}</td>
                    <td className="px-4 py-2">{String(stats.events_7d ?? 0)}</td>
                    <td className="px-4 py-2">{String(stats.activity_delta_7d ?? 0)}</td>
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
              {String(detailQ.data.declared_container_kind)} · expansion{" "}
              {String((detailQ.data.stats as Record<string, unknown>)?.expansion_level ?? "direct")}
            </p>
            <ul className="mt-3 max-h-96 space-y-1 overflow-y-auto text-sm">
              {((detailQ.data.memberships as Array<Record<string, unknown>>) ?? []).map((m) => (
                <li key={String(m.id)} className="rounded bg-stone-50 px-2 py-1">
                  {String(m.display_label ?? m.canon_entity_id)} · {String(m.extractor_rule)} · d
                  {String(m.seed_distance)}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
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
        <h1 className="text-xl font-semibold text-stone-900">Declared Domains</h1>
        <p className="mt-1 text-sm text-stone-600">
          Trusted execution containers (Linear initiatives and projects) with deterministic
          membership and momentum.
        </p>
        {data ? (
          <p className="mt-2 text-xs text-stone-500">
            {data.declared_domain_count} domains · {data.dirty_queue_pending} dirty
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
