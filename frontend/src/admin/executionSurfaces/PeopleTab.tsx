import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { executionSurfacesAdminPath } from "../../lib/adminApiUrl";
import { adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "../cortex/CortexPageSkeleton";
import { ObservationFootnote, OmissionBanner } from "./OmissionBanner";

export function PeopleTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams] = useSearchParams();
  const personId = searchParams.get("person_id");

  const listQ = useQuery({
    queryKey: ["execution-surface-people", tenantId],
    queryFn: () =>
      adminJson<{ items: Array<Record<string, unknown>> }>(
        executionSurfacesAdminPath(tenantId, "people", "limit=80"),
        undefined,
        { tenantIdHint: tenantId },
      ),
    enabled: Boolean(tenantId) && !personId,
  });

  const detailQ = useQuery({
    queryKey: ["execution-surface-person", tenantId, personId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        executionSurfacesAdminPath(tenantId, `people/${personId}`),
        undefined,
        { tenantIdHint: tenantId },
      ),
    enabled: Boolean(tenantId && personId),
  });

  if (personId) {
    if (detailQ.isLoading) return <CortexPageSkeleton label="Loading person" />;
    const p = detailQ.data;
    if (!p) return null;
    const participation = (p.participation ?? {}) as Record<string, unknown>;
    const domains = (p.domains ?? []) as Array<Record<string, unknown>>;
    return (
      <div className="space-y-4">
        <Link
          to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/people`}
          className="text-sm text-indigo-700 hover:underline"
        >
          ← All people
        </Link>
        <h2 className="text-xl font-semibold">{String(p.display_name)}</h2>
        <section className="rounded-xl border border-stone-200 bg-white p-4">
          <h3 className="font-semibold">Identity</h3>
          <ul className="mt-2 text-sm">
            {((p.accounts ?? []) as Array<Record<string, unknown>>).map((a) => (
              <li key={String(a.identity_account_id)}>
                {String(a.connector)} · {String(a.display_label)}
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl border border-stone-200 bg-white p-4">
          <h3 className="font-semibold">Participation (substrate touches)</h3>
          <ObservationFootnote text={String(participation.footnote ?? "")} />
          <p className="mt-2 text-sm">
            Work items: {String(participation.work_items ?? 0)} · PRs: {String(participation.pull_requests ?? 0)} ·
            Messages: {String(participation.messages ?? 0)} · Domains: {String(participation.domains ?? 0)}
          </p>
        </section>
        <section className="rounded-xl border border-stone-200 bg-white p-4">
          <h3 className="font-semibold">Declared domains</h3>
          {domains.length === 0 ? (
            <OmissionBanner
              omission={{
                code: "no_domains",
                message: "Not appearing in any declared domain participant set.",
                remediation: "Improve domain membership and identity linkage on artifacts.",
              }}
            />
          ) : (
            <ul className="mt-2 text-sm">
              {domains.map((d) => (
                <li key={String(d.id)}>
                  <Link
                    to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/domains/${d.id}`}
                    className="text-indigo-800 hover:underline"
                  >
                    {String(d.display_name)}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  }

  if (listQ.isLoading) return <CortexPageSkeleton label="Loading people" />;

  return (
    <div className="space-y-4">
      <ObservationFootnote text="Counts reflect substrate artifact touches, not performance rankings." />
      <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
        {(listQ.data?.items ?? []).map((p) => {
          const part = (p.participation ?? {}) as Record<string, unknown>;
          return (
            <li key={String(p.id)} className="px-4 py-3 text-sm">
              <Link
                to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/people?tab=people&person_id=${p.id}`}
                className="font-medium text-indigo-800 hover:underline"
              >
                {String(p.display_name)}
              </Link>
              <p className="text-xs text-stone-500">
                {String(part.work_items ?? 0)} work · {String(part.pull_requests ?? 0)} PRs ·{" "}
                {String(part.domains ?? 0)} domains
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
