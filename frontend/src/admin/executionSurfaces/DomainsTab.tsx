import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "../cortex/CortexPageSkeleton";
import { DomainDetailView } from "./DomainDetailView";
import type { DomainListItem } from "./executionSurfacesTypes";
import { ObservationFootnote } from "./OmissionBanner";

export function DomainsTab() {
  const { tenantId = "", domainId: domainIdParam } = useParams<{ tenantId: string; domainId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const sort = searchParams.get("sort") ?? "activity";
  const lifecycle = searchParams.get("lifecycle") ?? "";
  const domainId = domainIdParam ?? searchParams.get("domain_id");

  const listQ = useQuery({
    queryKey: ["execution-surface-domains", tenantId, sort, lifecycle],
    queryFn: () => {
      const params = new URLSearchParams({ sort, limit: "100" });
      if (lifecycle) params.set("lifecycle", lifecycle);
      return adminJson<{ items: DomainListItem[] }>(
        `/admin/tenants/${tenantId}/cortex/execution-surfaces/domains?${params}`,
      );
    },
  });

  if (domainId) {
    return <DomainDetailView domainId={domainId} />;
  }

  if (listQ.isLoading) return <CortexPageSkeleton label="Loading domains" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        Declared domains are execution scopes projected from canon seeds. Open a domain for the full picture — work,
        people, connected chains, and evidence.
      </p>
      <ObservationFootnote text="Activity columns reflect Cortex observation signals (materialization), not operational execution timelines." />
      <div className="flex flex-wrap gap-2">
        {(["", "active", "planned", "completed", "dormant"] as const).map((bucket) => (
          <button
            key={bucket || "all-lifecycle"}
            type="button"
            className={`rounded px-2 py-1 text-sm ${
              lifecycle === bucket ? "bg-indigo-100 text-indigo-900" : "bg-stone-100 text-stone-700"
            }`}
            onClick={() =>
              setSearchParams((prev) => {
                const p = new URLSearchParams(prev);
                p.set("tab", "domains");
                if (bucket) p.set("lifecycle", bucket);
                else p.delete("lifecycle");
                p.delete("domain_id");
                return p;
              })
            }
          >
            {bucket || "all lifecycle"}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {(["activity", "growing", "mass", "name"] as const).map((key) => (
          <button
            key={key}
            type="button"
            className={`rounded px-2 py-1 text-sm ${
              sort === key ? "bg-indigo-100 text-indigo-900" : "bg-stone-100 text-stone-700"
            }`}
            onClick={() =>
              setSearchParams((prev) => {
                const p = new URLSearchParams(prev);
                p.set("tab", "domains");
                p.set("sort", key);
                p.delete("domain_id");
                return p;
              })
            }
          >
            {key}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
            <tr>
              <th className="px-4 py-2">Domain</th>
              <th className="px-4 py-2">Kind</th>
              <th className="px-4 py-2">Lifecycle</th>
              <th className="px-4 py-2">Members</th>
              <th className="px-4 py-2">Obs. 7d</th>
              <th className="px-4 py-2">Δ 7d</th>
            </tr>
          </thead>
          <tbody>
            {(listQ.data?.items ?? []).map((row) => {
              const obs = row.observation_stats;
              return (
                <tr key={row.id} className="border-t border-stone-100 hover:bg-stone-50">
                  <td className="px-4 py-2">
                    <Link
                      to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/domains/${row.id}`}
                      className="font-medium text-indigo-800 hover:underline"
                    >
                      {row.display_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-xs">{row.declared_container_kind}</td>
                  <td className="px-4 py-2 text-xs capitalize">
                    {String((row as DomainListItem & { lifecycle_bucket?: string }).lifecycle_bucket ?? "—")}
                  </td>
                  <td className="px-4 py-2">{row.active_membership_count ?? 0}</td>
                  <td className="px-4 py-2">{obs?.events_7d ?? 0}</td>
                  <td className="px-4 py-2">{obs?.activity_delta_7d ?? 0}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
