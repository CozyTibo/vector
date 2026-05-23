import { useState, type ReactNode } from "react";

import { SectionSkeleton } from "../SectionSkeleton";
import { StatusBadge } from "../../ui/StatusBadge";
import { IdentityEntityCard } from "./IdentityEntityCard";
import type { GraphTruthInspectorPayload } from "./graphInspectorTypes";
import type { IdentitySearchParams } from "./identityContinuityTypes";
import {
  useIdentityContinuityEntity,
  useIdentityContinuityInspectorTenant,
  useIdentityContinuitySearch,
} from "./useIdentityContinuityInspector";

type Props = {
  data: GraphTruthInspectorPayload | undefined;
};

function severityTone(sev: string | undefined): "ok" | "warn" | "bad" {
  if (sev === "ok") return "ok";
  if (sev === "bad") return "bad";
  return "warn";
}

const SEARCH_FIELDS: Array<{ key: keyof IdentitySearchParams; label: string; placeholder: string }> = [
  { key: "slack_user_id", label: "Slack user id", placeholder: "U01234567" },
  { key: "github_login", label: "GitHub login", placeholder: "octocat" },
  { key: "notion_user_id", label: "Notion user id", placeholder: "notion-user-id" },
  { key: "email", label: "Email", placeholder: "person@company.com" },
  { key: "entity_id", label: "Entity / handle id", placeholder: "uuid" },
  { key: "canonical_entity_id", label: "Canonical entity id", placeholder: "uuid" },
];

export function IdentityContinuityInspector({ data }: Props) {
  const tenantQ = useIdentityContinuityInspectorTenant();
  const ic = tenantQ.data?.identity_continuity ?? data?.identity_continuity;
  const anchor = ic?.anchor_boundary ?? {};

  const [draft, setDraft] = useState<IdentitySearchParams>({});
  const [submitted, setSubmitted] = useState<IdentitySearchParams>({});
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  const searchQ = useIdentityContinuitySearch(submitted, Boolean(Object.values(submitted).some(Boolean)));
  const entityQ = useIdentityContinuityEntity(selectedEntityId);

  const onSearch = (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitted({ ...draft });
    setSelectedEntityId(null);
  };

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Identity search</h3>
        <p className="mt-1 text-xs text-stone-500">
          Resolve deterministic org entity ids from external keys. Results show candidate lineage,
          skip reasons, and promotion receipts.
        </p>
        <form onSubmit={onSearch} className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SEARCH_FIELDS.map(({ key, label, placeholder }) => (
            <label key={key} className="block text-sm">
              <span className="text-xs font-medium text-stone-600">{label}</span>
              <input
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
                placeholder={placeholder}
                value={draft[key] ?? ""}
                onChange={(e) => setDraft((prev) => ({ ...prev, [key]: e.target.value }))}
              />
            </label>
          ))}
          <div className="flex items-end">
            <button
              type="submit"
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Search
            </button>
          </div>
        </form>
      </section>

      {searchQ.isPending ? <SectionSkeleton variant="table" /> : null}
      {searchQ.isError ? (
        <p className="text-sm text-red-700">{(searchQ.error as Error).message}</p>
      ) : null}
      {searchQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Search matches</h3>
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-3 py-2">key</th>
                  <th className="px-3 py-2">value</th>
                  <th className="px-3 py-2">entity id</th>
                  <th className="px-3 py-2">found</th>
                </tr>
              </thead>
              <tbody>
                {searchQ.data.matches.map((match, idx) => (
                  <tr key={`${match.search_key}-${idx}`} className="border-b border-stone-100">
                    <td className="px-3 py-2">{match.search_key}</td>
                    <td className="px-3 py-2 font-mono text-xs">{match.value}</td>
                    <td className="px-3 py-2">
                      {match.entity_id ? (
                        <button
                          type="button"
                          className="font-mono text-xs text-indigo-700 underline"
                          onClick={() => setSelectedEntityId(match.entity_id!)}
                        >
                          {match.entity_id}
                        </button>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-2">{match.found ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {searchQ.data.entity_ids.length > 0 && !selectedEntityId ? (
            <p className="mt-3 text-xs text-stone-500">
              Click an entity id to inspect lineage, candidates, and evidence.
            </p>
          ) : null}
        </section>
      ) : null}

      {selectedEntityId ? (
        entityQ.isPending && !entityQ.data ? (
          <SectionSkeleton variant="cards" />
        ) : entityQ.isError ? (
          <p className="text-sm text-red-700">{(entityQ.error as Error).message}</p>
        ) : entityQ.data ? (
          <IdentityEntityCard data={entityQ.data} />
        ) : null
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Anchors" value={anchor.anchor_count?.toLocaleString() ?? "—"} />
        <Metric
          label="Anchors missing entity"
          value={
            <span className="flex items-center gap-2">
              {ic?.anchors_missing_org_entity_pct ?? "—"}%
              <StatusBadge tone={severityTone(ic?.anchors_missing_severity)}>
                {ic?.anchors_missing_severity ?? "unknown"}
              </StatusBadge>
            </span>
          }
        />
        <Metric label="Candidate rows" value={ic?.candidate_rows?.toLocaleString() ?? "—"} />
        <Metric
          label="Unpromoted"
          value={(tenantQ.data?.unpromoted_candidates ?? data?.unpromoted_candidates ?? 0).toLocaleString()}
        />
      </section>

      {(ic?.promotable_by_rule_id ?? []).length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Promotable candidates by rule (tenant)</h3>
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-3 py-2">rule_id</th>
                  <th className="px-3 py-2">promotable count</th>
                </tr>
              </thead>
              <tbody>
                {ic!.promotable_by_rule_id!.map((row: { rule_id: string; promotable_count: number }) => (
                  <tr key={row.rule_id} className="border-b border-stone-100">
                    <td className="px-3 py-2 font-mono text-xs">{row.rule_id}</td>
                    <td className="px-3 py-2 tabular-nums">{row.promotable_count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase text-stone-500">{label}</p>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

