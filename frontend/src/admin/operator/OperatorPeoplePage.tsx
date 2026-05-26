import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../cortex/SectionSkeleton";
import { DeployInfoFooter } from "./DeployInfoFooter";
import { OperatorDebugIdentityPanel } from "./OperatorDebugIdentityPanel";
import { OperatorPeopleRebuildPanel } from "./OperatorPeopleRebuildPanel";
import { useOperatorPeopleDirectory } from "./useOperatorPeople";

function initials(name: string | null, email: string | null): string {
  if (name) {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  }
  if (email) return email.slice(0, 2).toUpperCase();
  return "?";
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function OperatorPeoplePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const directoryQ = useOperatorPeopleDirectory(tenantId, { limit: 100, offset: 0 });

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">People</h1>
        <p className="mt-1 text-sm text-stone-600">
          Reconstructed identities across your connectors — browse the organization without searching by id.
        </p>
      </header>

      <OperatorPeopleRebuildPanel />
      <OperatorDebugIdentityPanel />

      {directoryQ.isPending && !directoryQ.data ? (
        <SectionSkeleton variant="table" />
      ) : directoryQ.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p className="font-medium">Could not load people directory</p>
          <p className="mt-1 text-red-800">{(directoryQ.error as Error).message}</p>
          <p className="mt-2 text-xs text-red-700">
            If this persists after deploy, the API may still be rolling out or the people query timed out — try Runtime
            to confirm the API is healthy.
          </p>
        </div>
      ) : directoryQ.data ? (
        <>
          <p className="text-xs text-stone-500">
            {directoryQ.data.total} reconstructed {directoryQ.data.total === 1 ? "person" : "people"}
            {directoryQ.data.raw_entity_count > directoryQ.data.total
              ? ` (${directoryQ.data.raw_entity_count} raw identity rows merged by link)`
              : ""}
          </p>

          {directoryQ.data.people.length === 0 ? (
            <section className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-8 text-center">
              <p className="text-sm font-medium text-stone-800">No people reconstructed yet</p>
              <p className="mt-2 text-sm text-stone-600">
                Run ingestion and identity phases first. People appear here once human actors are materialized from
                Slack, GitHub, Notion, and email.
              </p>
            </section>
          ) : (
            <section className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
              <ul className="divide-y divide-stone-100">
                {directoryQ.data.people.map((person) => {
                  const label = person.display_name || person.email || "Unknown person";
                  return (
                    <li key={person.person_id}>
                      <Link
                        to={`/admin/tenants/${tenantId}/cortex/people/${person.person_id}`}
                        className="flex items-center gap-4 px-5 py-4 no-underline transition hover:bg-stone-50"
                      >
                        <div
                          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-800"
                          aria-hidden
                        >
                          {initials(person.display_name, person.email)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-stone-900">{label}</p>
                          <p className="truncate text-sm text-stone-600">{person.email ?? "No email on file"}</p>
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            {person.systems.map((sys) => (
                              <span
                                key={sys}
                                className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-700"
                              >
                                {sys}
                              </span>
                            ))}
                            {person.linked_account_count > 1 ? (
                              <span className="text-xs text-stone-500">
                                {person.linked_account_count} linked accounts
                              </span>
                            ) : null}
                            {person.in_auth_graph ? (
                              <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800">
                                In graph
                              </span>
                            ) : null}
                          </div>
                        </div>
                        <div className="hidden shrink-0 text-right sm:block">
                          {person.title ? <p className="text-xs text-stone-600">{person.title}</p> : null}
                          <p className="text-xs text-stone-500">Last seen {fmtTime(person.last_seen_at)}</p>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
