import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type {
  CortexConnectorId,
  CortexRawIngestionRecord,
  CortexRawIngestionRecords,
  CortexRawIngestionStats,
} from "../cortexAdminTypes";
import { titleConnector } from "../cortexAdminTypes";
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

function jsonBlock(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function IngestionRawDataTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const connector = (searchParams.get("raw_connector") ?? "slack") as CortexConnectorId;
  const resourceType = searchParams.get("raw_type") ?? "";
  const searchDraft = searchParams.get("raw_q") ?? "";
  const [searchInput, setSearchInput] = useState(searchDraft);
  const includeHealth = searchParams.get("raw_health") === "1";
  const page = Math.max(0, Number.parseInt(searchParams.get("raw_page") ?? "0", 10) || 0);
  const offset = page * PAGE_SIZE;
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    setSearchInput(searchDraft);
  }, [searchDraft]);

  const patchParams = (patch: Record<string, string | null>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", "raw");
      for (const [key, value] of Object.entries(patch)) {
        if (value === null || value === "") next.delete(key);
        else next.set(key, value);
      }
      return next;
    });
  };

  const statsQ = useQuery({
    queryKey: ["admin-cortex-raw-stats", tenantId, connector],
    queryFn: () => {
      const params = new URLSearchParams({ connector });
      return adminJson<CortexRawIngestionStats>(
        `/admin/tenants/${tenantId}/cortex/ingestion/raw-stats?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const resourceTypeOptions = useMemo(() => {
    const rows = statsQ.data?.resources ?? [];
    const types = [...new Set(rows.map((r) => r.resource_type))].sort();
    return types;
  }, [statsQ.data?.resources]);

  const recordsQ = useQuery({
    queryKey: [
      "admin-cortex-raw-records",
      tenantId,
      connector,
      resourceType,
      searchDraft,
      includeHealth,
      page,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      if (resourceType) params.set("resource_type", resourceType);
      if (searchDraft.trim()) params.set("search_query", searchDraft.trim());
      if (includeHealth) params.set("include_health_rows", "true");
      return adminJson<CortexRawIngestionRecords>(
        `/admin/tenants/${tenantId}/cortex/ingestion/connectors/${connector}/raw-records?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const data = recordsQ.data;
  const items: CortexRawIngestionRecord[] = data?.items ?? [];
  const total = data?.total_count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  const toggleExpanded = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const applySearch = () => {
    patchParams({ raw_q: searchInput.trim() || null, raw_page: null });
  };

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-stone-900">Raw ingested data</h2>
        <p className="text-sm text-stone-600">
          Browse append-only rows in <code className="text-xs">raw_ingestion_records</code> — up to{" "}
          {PAGE_SIZE} per page. Expand a row to inspect payload JSON.
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-xs text-stone-600">
          Connector
          <select
            className="mt-1 block rounded border border-stone-300 bg-white px-2 py-1.5 text-sm"
            value={connector}
            onChange={(e) => {
              setExpandedIds(new Set());
              patchParams({
                raw_connector: e.target.value,
                raw_type: null,
                raw_page: null,
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
          Resource type
          <select
            className="mt-1 block min-w-[12rem] rounded border border-stone-300 bg-white px-2 py-1.5 text-sm"
            value={resourceType}
            onChange={(e) => {
              setExpandedIds(new Set());
              patchParams({ raw_type: e.target.value || null, raw_page: null });
            }}
          >
            <option value="">All types</option>
            {resourceTypeOptions.map((rt) => (
              <option key={rt} value={rt}>
                {rt}
              </option>
            ))}
          </select>
        </label>

        <label className="min-w-[14rem] flex-1 text-xs text-stone-600">
          Search (external id, payload, keys…)
          <div className="mt-1 flex gap-2">
            <input
              type="search"
              className="w-full rounded border border-stone-300 px-2 py-1.5 text-sm"
              value={searchInput}
              placeholder="e.g. issue id, message ts, email…"
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

        <label className="flex items-center gap-2 pb-1 text-xs text-stone-600">
          <input
            type="checkbox"
            checked={includeHealth}
            onChange={(e) => {
              setExpandedIds(new Set());
              patchParams({ raw_health: e.target.checked ? "1" : null, raw_page: null });
            }}
          />
          Include health / ping rows
        </label>
      </div>

      {statsQ.isSuccess && resourceTypeOptions.length > 0 ? (
        <p className="mt-2 text-xs text-stone-500">
          {titleConnector(connector)}: {resourceTypeOptions.length} resource type(s) in store
          {resourceType
            ? ` · filtered to ${resourceType}`
            : ` · ${total.toLocaleString()} row(s) match filters`}
        </p>
      ) : null}

      {recordsQ.isPending && !data ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : recordsQ.isError ? (
        <p className="mt-4 text-sm text-red-700">{(recordsQ.error as Error).message}</p>
      ) : items.length === 0 ? (
        <p className="mt-4 text-sm text-stone-600">
          No raw rows match these filters for {titleConnector(connector)}.
        </p>
      ) : (
        <>
          <p className="mt-3 text-xs text-stone-500">
            Showing {from.toLocaleString()}–{to.toLocaleString()} of {total.toLocaleString()} row(s)
            · newest first
          </p>
          <ul className="mt-3 space-y-2">
            {items.map((row) => {
              const open = expandedIds.has(row.id);
              return (
                <li
                  key={row.id}
                  className="rounded-lg border border-stone-200 bg-stone-50/60 overflow-hidden"
                >
                  <button
                    type="button"
                    className="flex w-full flex-wrap items-start gap-x-4 gap-y-1 px-3 py-2.5 text-left hover:bg-stone-100/80"
                    onClick={() => toggleExpanded(row.id)}
                    aria-expanded={open}
                  >
                    <span className="shrink-0 text-xs font-medium text-indigo-700">
                      {open ? "▼" : "▶"}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="font-mono text-xs text-stone-800">{row.resource_type}</span>
                      <span className="mx-2 text-stone-400">·</span>
                      <span className="break-all font-mono text-xs text-stone-700">
                        {row.external_id}
                      </span>
                    </span>
                    <span className="text-xs text-stone-500">{formatWhen(row.fetched_at)}</span>
                    <span className="text-xs text-stone-500">HTTP {row.http_status}</span>
                  </button>
                  {open ? (
                    <div className="border-t border-stone-200 bg-white px-3 py-3 text-xs">
                      <dl className="grid gap-1 sm:grid-cols-2">
                        <div>
                          <dt className="text-stone-500">Row id</dt>
                          <dd className="font-mono text-stone-800">{row.id}</dd>
                        </div>
                        <div>
                          <dt className="text-stone-500">Run id</dt>
                          <dd className="break-all font-mono text-stone-800">{row.run_id}</dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="text-stone-500">API endpoint</dt>
                          <dd className="break-all font-mono text-stone-800">{row.api_endpoint}</dd>
                        </div>
                        {row.source_identity_key ? (
                          <div className="sm:col-span-2">
                            <dt className="text-stone-500">Source identity</dt>
                            <dd className="break-all font-mono text-stone-800">
                              {row.source_identity_key}
                            </dd>
                          </div>
                        ) : null}
                        {row.source_revision_key ? (
                          <div className="sm:col-span-2">
                            <dt className="text-stone-500">Source revision</dt>
                            <dd className="break-all font-mono text-stone-800">
                              {row.source_revision_key}
                            </dd>
                          </div>
                        ) : null}
                        {row.replay_job_id ? (
                          <div>
                            <dt className="text-stone-500">Replay job</dt>
                            <dd className="break-all font-mono text-stone-800">
                              {row.replay_job_id}
                            </dd>
                          </div>
                        ) : null}
                      </dl>
                      <p className="mt-3 font-medium text-stone-700">Query params</p>
                      <pre className="mt-1 max-h-48 overflow-auto rounded border border-stone-200 bg-stone-50 p-2 font-mono text-[11px] leading-relaxed text-stone-800">
                        {jsonBlock(row.query_params)}
                      </pre>
                      <p className="mt-3 font-medium text-stone-700">Payload body</p>
                      <pre className="mt-1 max-h-[28rem] overflow-auto rounded border border-stone-200 bg-stone-50 p-2 font-mono text-[11px] leading-relaxed text-stone-800">
                        {jsonBlock(row.payload_body)}
                      </pre>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
          {total > PAGE_SIZE ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
                disabled={page <= 0}
                onClick={() => {
                  setExpandedIds(new Set());
                  patchParams({ raw_page: page <= 1 ? null : String(page - 1) });
                }}
              >
                Previous
              </button>
              <span className="text-xs text-stone-600">
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
                disabled={page + 1 >= pageCount}
                onClick={() => {
                  setExpandedIds(new Set());
                  patchParams({ raw_page: String(page + 1) });
                }}
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
