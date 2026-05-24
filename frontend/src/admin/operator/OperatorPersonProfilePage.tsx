import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../cortex/SectionSkeleton";
import type { OperatorPersonActivity } from "./operatorTypes";
import { DeployInfoFooter } from "./DeployInfoFooter";
import { useOperatorPersonProfile } from "./useOperatorPeople";

function initials(name: string | null, email: string | null): string {
  if (name) {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  }
  if (email) return email.slice(0, 2).toUpperCase();
  return "?";
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function kindIcon(kind: string): string {
  switch (kind) {
    case "message":
      return "Message";
    case "pull_request":
      return "Pull request";
    case "issue":
      return "Issue";
    case "document":
    case "page":
      return "Document";
    case "workflow_run":
      return "Workflow";
    case "meeting":
    case "transcript":
      return "Meeting";
    default:
      return kind.replace(/_/g, " ");
  }
}

function ActivityRow({ item }: { item: OperatorPersonActivity }) {
  return (
    <li className="flex gap-3 border-b border-stone-100 px-4 py-3 last:border-b-0">
      <div className="mt-0.5 w-24 shrink-0 text-xs text-stone-500">{fmtDateTime(item.occurred_at)}</div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
          {item.connector} · {kindIcon(item.kind)}
        </p>
        <p className="mt-1 text-sm text-stone-900">{item.title}</p>
        {item.external_id ? (
          <p className="mt-1 truncate font-mono text-xs text-stone-500">{item.external_id}</p>
        ) : null}
      </div>
    </li>
  );
}

export default function OperatorPersonProfilePage() {
  const { tenantId = "", personId = "" } = useParams<{ tenantId: string; personId: string }>();
  const profileQ = useOperatorPersonProfile(tenantId, personId || null);

  if (!personId) {
    return <p className="text-sm text-red-700">Missing person id.</p>;
  }

  const profile = profileQ.data;
  const label = profile?.display_name || profile?.email || "Unknown person";

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <Link
          to={`/admin/tenants/${tenantId}/cortex/people`}
          className="text-xs font-medium text-indigo-700 no-underline hover:underline"
        >
          ← Back to people
        </Link>

        {profileQ.isPending && !profile ? (
          <SectionSkeleton variant="cards" />
        ) : profileQ.isError ? (
          <p className="mt-4 text-sm text-red-700">{(profileQ.error as Error).message}</p>
        ) : profile ? (
          <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xl font-semibold text-indigo-800"
              aria-hidden
            >
              {initials(profile.display_name, profile.email)}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold text-stone-900">{label}</h1>
              {profile.email ? <p className="mt-1 text-sm text-stone-600">{profile.email}</p> : null}
              {profile.title ? <p className="mt-1 text-sm text-stone-600">{String(profile.title)}</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {profile.systems.map((sys) => (
                  <span
                    key={sys}
                    className="rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-medium text-stone-700"
                  >
                    {sys}
                  </span>
                ))}
                {profile.entity_ids.length > 1 ? (
                  <span className="text-xs text-stone-500">{profile.entity_ids.length} merged identity rows</span>
                ) : null}
              </div>
              <p className="mt-3 text-xs text-stone-500">
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/inspect/identity/e/${profile.person_id}`}
                  className="font-medium text-indigo-700"
                >
                  Open forensic identity inspect
                </Link>
                {" · "}
                {profile.evidence_anchor_count ?? 0} evidence anchors · {profile.authoritative_link_count} auth links
              </p>
            </div>
          </div>
        ) : null}
      </header>

      {profile ? (
        <>
          {Object.keys(profile.work_summary).length > 0 ? (
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-stone-900">Work we know about</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(profile.work_summary)
                  .sort((a, b) => b[1] - a[1])
                  .map(([kind, count]) => (
                    <span
                      key={kind}
                      className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-800"
                    >
                      {count} {kindIcon(kind)}
                      {count === 1 ? "" : "s"}
                    </span>
                  ))}
              </div>
            </section>
          ) : null}

          {profile.accounts.length > 0 ? (
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-stone-900">Connected accounts</h2>
              <ul className="mt-3 divide-y divide-stone-100 rounded-lg border border-stone-200">
                {profile.accounts.map((account) => (
                  <li key={`${account.entity_id}-${account.projection_kind}`} className="px-4 py-3 text-sm">
                    <p className="font-medium text-stone-900">
                      {account.system}
                      {account.is_primary ? " · primary" : ""}
                    </p>
                    <p className="mt-0.5 text-stone-600">{account.detail}</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-xl border border-stone-200 bg-white shadow-sm">
            <div className="border-b border-stone-100 px-5 py-4">
              <h2 className="text-sm font-semibold text-stone-900">Activity</h2>
              <p className="mt-1 text-xs text-stone-500">
                Messages, PRs, issues, and documents tied to this person through canonical evidence.
              </p>
              <p className="mt-1 text-xs text-stone-500">
                Showing {profile.activity.length} of {profile.activity_total}
              </p>
            </div>
            {profile.activity.length === 0 ? (
              <p className="px-5 py-8 text-sm text-stone-600">No related activity found yet for this identity.</p>
            ) : (
              <ul>{profile.activity.map((item) => <ActivityRow key={item.activity_id} item={item} />)}</ul>
            )}
          </section>

          {profile.related_people.length > 0 ? (
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-stone-900">Related people</h2>
              <ul className="mt-3 space-y-2">
                {profile.related_people.map((other) => (
                  <li key={other.person_id}>
                    <Link
                      to={`/admin/tenants/${tenantId}/cortex/people/${other.person_id}`}
                      className="text-sm font-medium text-indigo-700 no-underline hover:underline"
                    >
                      {other.display_name || other.email || other.person_id.slice(0, 8)}
                    </Link>
                    {other.link_type ? (
                      <span className="ml-2 text-xs text-stone-500">via {other.link_type}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {profile.retrieval_entries.length > 0 ? (
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-stone-900">Retrieval index</h2>
              <p className="mt-1 text-xs text-stone-500">{profile.retrieval_total} indexed entries mention this person.</p>
              <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                    <tr>
                      <th className="px-3 py-2">Kind</th>
                      <th className="px-3 py-2">Key</th>
                      <th className="px-3 py-2">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.retrieval_entries.map((row, idx) => (
                      <tr key={idx} className="border-b border-stone-100">
                        <td className="px-3 py-2 font-mono text-xs">{String(row.index_kind ?? "—")}</td>
                        <td className="max-w-md truncate px-3 py-2 font-mono text-xs">
                          {String(row.index_key ?? row.retrieval_lookup_id ?? "—")}
                        </td>
                        <td className="px-3 py-2 text-xs">{fmtDateTime(String(row.created_at ?? ""))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Link
                to={`/admin/tenants/${tenantId}/cortex/inspect/retrieval?entity_id=${profile.person_id}`}
                className="mt-3 inline-block text-xs font-medium text-indigo-700 no-underline hover:underline"
              >
                Open retrieval inspect →
              </Link>
            </section>
          ) : null}
        </>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
