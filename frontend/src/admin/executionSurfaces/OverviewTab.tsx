import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "../cortex/CortexPageSkeleton";
import { ConnectedWorkChains } from "./ConnectedWorkChains";
import { OmissionBanner, ObservationFootnote } from "./OmissionBanner";
import type { ConnectedWorkChain, DomainListItem } from "./executionSurfacesTypes";

type Overview = {
  substrate: { advisories: Array<{ code: string; message: string; remediation: string | null }> };
  observation_footnote: string;
  active_domains: DomainListItem[];
  active_people: Array<Record<string, unknown>>;
  recent_observation_activity: Array<Record<string, unknown>>;
  activity_meta: Record<string, unknown>;
  connected_work: {
    chains: Array<ConnectedWorkChain & { domain_id?: string; domain_name?: string }>;
    omission: { code: string; message: string; remediation: string | null } | null;
  };
  hero_route_hint: string;
};

export function OverviewTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["execution-surface-overview", tenantId],
    queryFn: () =>
      adminJson<Overview>(`/admin/tenants/${tenantId}/cortex/execution-surfaces/overview`),
  });

  if (q.isLoading) return <CortexPageSkeleton label="Loading overview" />;
  if (!q.data) return null;

  return (
    <div className="space-y-6">
      <p className="text-sm text-stone-600">{q.data.hero_route_hint}</p>
      <ObservationFootnote text={q.data.observation_footnote} />
      {(q.data.substrate.advisories ?? []).map((a) => (
        <OmissionBanner key={a.code} omission={a} />
      ))}

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <ConnectedWorkChains
          chains={q.data.connected_work.chains}
          omission={q.data.connected_work.omission}
        />
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-stone-900">Declared domains</h3>
          <Link
            to={`/admin/tenants/${tenantId}/cortex/execution-surfaces?tab=domains`}
            className="text-sm text-indigo-700 hover:underline"
          >
            View all →
          </Link>
        </div>
        <ul className="mt-3 divide-y divide-stone-100 text-sm">
          {q.data.active_domains.map((d) => (
            <li key={d.id} className="py-2">
              <Link
                to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/domains/${d.id}`}
                className="font-medium text-indigo-800 hover:underline"
              >
                {d.display_name}
              </Link>
              <span className="ml-2 text-stone-500">
                obs. 7d: {d.observation_stats?.events_7d ?? 0}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-stone-900">Recent observation activity</h3>
          <Link
            to={`/admin/tenants/${tenantId}/cortex/execution-surfaces?tab=activity`}
            className="text-sm text-indigo-700 hover:underline"
          >
            Full stream →
          </Link>
        </div>
        <ObservationFootnote text={String(q.data.activity_meta?.footnote ?? q.data.observation_footnote)} />
        <ul className="mt-3 divide-y divide-stone-100 text-sm">
          {q.data.recent_observation_activity.map((ev) => (
            <li key={String(ev.id)} className="py-2">
              <p className="font-medium">{String(ev.label)}</p>
              <p className="text-xs text-stone-500">{String(ev.observed_at)}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-stone-900">People</h3>
          <Link
            to={`/admin/tenants/${tenantId}/cortex/execution-surfaces?tab=people`}
            className="text-sm text-indigo-700 hover:underline"
          >
            View all →
          </Link>
        </div>
        <ul className="mt-3 divide-y divide-stone-100 text-sm">
          {q.data.active_people.map((p) => (
            <li key={String(p.id)} className="py-2">
              <Link
                to={`/admin/tenants/${tenantId}/cortex/execution-surfaces?tab=people&person_id=${p.id}`}
                className="font-medium text-indigo-800 hover:underline"
              >
                {String(p.display_name)}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
