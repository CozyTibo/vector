import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CanonEntityItem, CanonEntityList, CanonEntityStats } from "../cortexAdminTypes";
import { titleConnector, type CortexConnectorId } from "../cortexAdminTypes";
import { SectionSkeleton } from "./SectionSkeleton";

const PAGE_SIZE = 50;

const CONNECTORS: { value: CortexConnectorId; label: string }[] = [
  { value: "slack", label: "Slack" },
  { value: "github", label: "GitHub" },
  { value: "linear", label: "Linear" },
  { value: "notion", label: "Notion" },
  { value: "calls", label: "Calls" },
];

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function CanonEntitiesListingTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const connector = (searchParams.get("canon_connector") ?? "github") as CortexConnectorId;
  const entityType = searchParams.get("canon_type") ?? "";
  const searchDraft = searchParams.get("canon_q") ?? "";
  const [searchInput, setSearchInput] = useState(searchDraft);
  const page = Math.max(0, Number.parseInt(searchParams.get("canon_page") ?? "0", 10) || 0);
  const offset = page * PAGE_SIZE;

  const patchParams = (patch: Record<string, string | null>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", "entities");
      for (const [key, value] of Object.entries(patch)) {
        if (value === null || value === "") next.delete(key);
        else next.set(key, value);
      }
      return next;
    });
  };

  const statsQ = useQuery({
    queryKey: ["admin-cortex-canon-stats", tenantId, connector],
    queryFn: () => {
      const params = new URLSearchParams({ connector });
      return adminJson<CanonEntityStats>(
        `/admin/tenants/${tenantId}/cortex/canon/stats?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const entityTypeOptions = useMemo(() => {
    const rows = statsQ.data?.resources ?? [];
    return [...new Set(rows.map((r) => r.entity_type))].sort();
  }, [statsQ.data?.resources]);

  const listQ = useQuery({
    queryKey: ["admin-cortex-canon-entities", tenantId, connector, entityType, searchDraft, page],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      params.set("connector", connector);
      if (entityType) params.set("entity_type", entityType);
      if (searchDraft.trim()) params.set("search", searchDraft.trim());
      return adminJson<CanonEntityList>(
        `/admin/tenants/${tenantId}/cortex/canon/entities?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const items: CanonEntityItem[] = listQ.data?.items ?? [];
  const total = listQ.data?.total_count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  const applySearch = () => {
    patchParams({ canon_q: searchInput.trim() || null, canon_page: null });
  };

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-stone-900">Canon entities by type</h2>
        <p className="text-sm text-stone-600">
          Browse materialized rows in <code className="text-xs">canon_entities</code> — filter by
          connector and entity type. Open a row for provenance back to raw.
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-xs text-stone-600">
          Connector
          <select
            className="mt-1 block rounded border border-stone-300 bg-white px-2 py-1.5 text-sm"
            value={connector}
            onChange={(e) => {
              patchParams({
                canon_connector: e.target.value,
                canon_type: null,
                canon_page: null,
              });
            }}
          >
            {CONNECTORS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs text-stone-600">
          Entity type
          <select
            className="mt-1 block min-w-[12rem] rounded border border-stone-300 bg-white px-2 py-1.5 text-sm"
            value={entityType}
            onChange={(e) => {
              patchParams({ canon_type: e.target.value || null, canon_page: null });
            }}
          >
            <option value="">All types</option>
            {entityTypeOptions.map((et) => (
              <option key={et} value={et}>
                {et}
              </option>
            ))}
          </select>
        </label>

        <label className="min-w-[14rem] flex-1 text-xs text-stone-600">
          Search label or entity key
          <div className="mt-1 flex gap-2">
            <input
              type="search"
              className="w-full rounded border border-stone-300 px-2 py-1.5 text-sm"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") applySearch();
              }}
            />
            <button
              type="button"
              className="shrink-0 rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
              onClick={applySearch}
            >
              Search
            </button>
          </div>
        </label>
      </div>

      {statsQ.isSuccess && entityTypeOptions.length > 0 ? (
        <p className="mt-2 text-xs text-stone-500">
          {titleConnector(connector)}: {entityTypeOptions.length} entity type(s) materialized
          {entityType ? ` · filtered to ${entityType}` : ` · ${total.toLocaleString()} match`}
        </p>
      ) : null}

      {listQ.isPending && !listQ.data ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : listQ.isError ? (
        <p className="mt-4 text-sm text-red-700">{(listQ.error as Error).message}</p>
      ) : items.length === 0 ? (
        <p className="mt-4 text-sm text-stone-600">
          No canon entities match these filters for {titleConnector(connector)}. Run a canon pass
          after ingestion has raw rows.
        </p>
      ) : (
        <>
          <p className="mt-3 text-xs text-stone-500">
            Showing {from.toLocaleString()}–{to.toLocaleString()} of {total.toLocaleString()} ·
            newest first
          </p>
          <ul className="mt-3 space-y-2">
            {items.map((e) => (
              <li
                key={e.id}
                className="rounded-lg border border-stone-200 bg-stone-50/60 px-3 py-2.5"
              >
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/canon/entities/${e.id}`}
                  className="font-medium text-indigo-700 hover:underline"
                >
                  {e.display_label}
                </Link>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-stone-600">
                  <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-900">
                    {e.entity_type}
                  </span>
                  <span>{titleConnector(e.connector)}</span>
                  <span>{formatWhen(e.materialized_at)}</span>
                  <span className="font-mono text-stone-500 truncate max-w-md" title={e.entity_key}>
                    {e.entity_key}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          {total > PAGE_SIZE ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium disabled:opacity-40"
                disabled={page <= 0}
                onClick={() => patchParams({ canon_page: page <= 1 ? null : String(page - 1) })}
              >
                Previous
              </button>
              <span className="text-xs text-stone-600">
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium disabled:opacity-40"
                disabled={page + 1 >= pageCount}
                onClick={() => patchParams({ canon_page: String(page + 1) })}
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
