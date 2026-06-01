import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "../cortex/CortexPageSkeleton";
import { ConnectedWorkChains } from "./ConnectedWorkChains";
import type { DomainSurfaceDetail } from "./executionSurfacesTypes";
import { OmissionBanner, ObservationFootnote, SectionHeader } from "./OmissionBanner";

function ArtifactList({
  section,
  tenantId,
}: {
  section: DomainSurfaceDetail["current_work"]["work_items"];
  tenantId: string;
}) {
  return (
    <div className="space-y-2">
      <OmissionBanner omission={section.omission} />
      <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
        {section.items.map((item) => (
          <li key={String(item.canon_entity_id)} className="px-3 py-2 text-sm">
            <Link
              to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/work/${String(item.canon_entity_id)}`}
              className="font-medium text-indigo-800 hover:underline"
            >
              {String(item.display_label)}
            </Link>
            <p className="text-xs text-stone-500">
              {String(item.connector)} · {String(item.entity_type)}
            </p>
            {item.membership ? (
              <p className="mt-1 font-mono text-xs text-stone-600">
                {String((item.membership as Record<string, unknown>).extractor_rule)}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DomainDetailView({ domainId }: { domainId: string }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["execution-surface-domain", tenantId, domainId],
    queryFn: () =>
      adminJson<DomainSurfaceDetail>(
        `/admin/tenants/${tenantId}/cortex/execution-surfaces/domains/${domainId}`,
      ),
  });

  if (q.isLoading) return <CortexPageSkeleton label="Loading domain" />;
  if (q.isError || !q.data) {
    return <p className="text-sm text-red-700">Could not load domain.</p>;
  }

  const d = q.data;
  const stats = d.summary.stats ?? {};

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/admin/tenants/${tenantId}/cortex/execution-surfaces?tab=domains`}
          className="text-sm text-indigo-700 hover:underline"
        >
          ← All domains
        </Link>
        <h2 className="mt-2 text-2xl font-semibold text-stone-900">{d.display_name}</h2>
        <p className="text-sm text-stone-600">
          {d.declared_container_kind} · {d.seed_connector}
          {d.seed_provider_status ? ` · ${d.seed_provider_status}` : ""}
          {d.lifecycle_bucket ? ` · ${d.lifecycle_bucket}` : ""}
        </p>
        <p className="mt-2 text-sm text-stone-700">{d.why_belong_together}</p>
      </div>

      {(d.summary.substrate.advisories ?? []).length > 0 ? (
        <div className="space-y-2">
          {d.summary.substrate.advisories.map((a) => (
            <OmissionBanner key={a.code} omission={a} />
          ))}
        </div>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-stone-900">Domain summary</h3>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-stone-500">Members</dt>
            <dd className="font-medium">{d.summary.member_count}</dd>
          </div>
          <div>
            <dt className="text-stone-500">Observation events (7d)</dt>
            <dd className="font-medium">{String(stats.observation_events_7d ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-stone-500">Mass</dt>
            <dd className="font-medium">{String(stats.mass_total ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-stone-500">Expansion</dt>
            <dd className="font-medium">{String(stats.expansion_level ?? "—")}</dd>
          </div>
        </dl>
        <div className="mt-3">
          <ObservationFootnote text={String(stats.footnote ?? "")} />
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <ConnectedWorkChains chains={d.connected_work.chains} omission={d.connected_work.omission} />
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm space-y-6">
        <h3 className="text-lg font-semibold text-stone-900">Current work</h3>
        <div>
          <SectionHeader title="Issues" count={d.current_work.work_items.count} />
          <ArtifactList section={d.current_work.work_items} tenantId={tenantId} />
        </div>
        <div>
          <SectionHeader title="PRs" count={d.current_work.pull_requests.count} />
          <ArtifactList section={d.current_work.pull_requests} tenantId={tenantId} />
        </div>
        <div>
          <SectionHeader title="Docs" count={d.current_work.documents.count} />
          <ArtifactList section={d.current_work.documents} tenantId={tenantId} />
        </div>
        <div>
          <SectionHeader title="Deployments" count={d.current_work.deployments.count} />
          <ArtifactList section={d.current_work.deployments} tenantId={tenantId} />
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <SectionHeader title="People" count={d.people.participants.length} />
        <OmissionBanner omission={d.people.omission} />
        <ul className="mt-2 space-y-2 text-sm">
          {d.people.owners.map((p) => (
            <li key={String(p.identity_id)}>
              <Link
                to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/people/${p.identity_id}`}
                className="text-indigo-800 hover:underline"
              >
                {String(p.display_name)} (owner)
              </Link>
            </li>
          ))}
          {d.people.participants
            .filter((p) => !d.people.owners.some((o) => o.identity_id === p.identity_id))
            .map((p) => (
              <li key={String(p.identity_id)}>
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/people/${p.identity_id}`}
                  className="text-indigo-800 hover:underline"
                >
                  {String(p.display_name)}
                </Link>
              </li>
            ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-stone-900">Activity</h3>
        <ObservationFootnote text={d.activity.footnote} />
        <OmissionBanner omission={d.activity.omission} />
        <ul className="mt-3 space-y-2 text-sm">
          {d.activity.observation_signals.map((sig, i) => (
            <li key={i} className="rounded border border-stone-100 p-2">
              <p className="font-medium">{String(sig.label)}</p>
              <p className="text-xs text-stone-500">{String(sig.observed_at)}</p>
              <p className="font-mono text-xs text-stone-600">
                {String((sig.provenance as Record<string, unknown>)?.extractor_rule ?? "")}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm space-y-4">
        <h3 className="font-semibold text-stone-900">Conversations</h3>
        <div>
          <SectionHeader title="Slack & discussions" count={d.conversations.slack_and_threads.count} />
          <OmissionBanner omission={d.conversations.slack_and_threads.omission} />
        </div>
        <div>
          <SectionHeader title="Meetings" count={d.conversations.meetings.count} />
          <OmissionBanner omission={d.conversations.meetings.omission} />
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-stone-900">Evidence</h3>
        <p className="mt-1 text-sm text-stone-600">Why Cortex grouped artifacts into this domain.</p>
        <h4 className="mt-4 text-sm font-medium text-stone-800">Membership rules</h4>
        <ul className="mt-2 max-h-48 overflow-auto font-mono text-xs text-stone-700">
          {d.evidence.membership_rules.map((m, i) => (
            <li key={i} className="border-b border-stone-100 py-1">
              {String(m.extractor_rule)} · {String(m.evidence_ref)}
            </li>
          ))}
        </ul>
        <h4 className="mt-4 text-sm font-medium text-stone-800">Graph rules</h4>
        <ul className="mt-2 max-h-48 overflow-auto font-mono text-xs text-stone-700">
          {d.evidence.graph_rules.map((g, i) => (
            <li key={i} className="border-b border-stone-100 py-1">
              {String(g.relationship_kind)} · {String(g.extractor_rule)}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
