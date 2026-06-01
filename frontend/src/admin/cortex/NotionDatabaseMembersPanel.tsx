import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { NotionDatabaseMembers } from "../cortexAdminTypes";

const PAGE_SIZE = 50;

function isNotionDatabaseEntity(entityKey: string, attrs: Record<string, unknown>): boolean {
  if (entityKey.includes(":notion:notion.database:")) {
    return true;
  }
  return attrs.declared_container_kind === "work_database";
}

export function NotionDatabaseMembersPanel({
  entityKey,
  attrsJson,
}: {
  entityKey: string;
  attrsJson: Record<string, unknown>;
}) {
  const { tenantId = "", entityId = "" } = useParams<{ tenantId: string; entityId: string }>();
  const [page, setPage] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const enabled =
    Boolean(tenantId && entityId) && isNotionDatabaseEntity(entityKey, attrsJson);

  const membersQ = useQuery({
    queryKey: ["admin-cortex-notion-database-members", tenantId, entityId, page, search],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (search.trim()) {
        params.set("search", search.trim());
      }
      return adminJson<NotionDatabaseMembers>(
        `/admin/tenants/${tenantId}/cortex/canon/entities/${entityId}/database-members?${params}`,
      );
    },
    enabled,
    placeholderData: (prev) => prev,
  });

  const pageInfo = useMemo(() => {
    const total = membersQ.data?.total_count ?? 0;
    const start = total === 0 ? 0 : page * PAGE_SIZE + 1;
    const end = Math.min((page + 1) * PAGE_SIZE, total);
    const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
    return { total, start, end, pageCount };
  }, [membersQ.data?.total_count, page]);

  if (!enabled) {
    return null;
  }

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">Database rows</h3>
          <p className="mt-1 text-xs text-stone-500">
            Canon documents with <code className="text-[11px]">database_id</code> matching this Notion database.
          </p>
        </div>
        {membersQ.data ? (
          <p className="text-sm text-stone-600">
            {membersQ.data.total_count.toLocaleString()} row
            {membersQ.data.total_count === 1 ? "" : "s"}
          </p>
        ) : null}
      </div>

      <form
        className="mt-3 flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(0);
          setSearch(searchInput.trim());
        }}
      >
        <input
          type="search"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Filter by title or id…"
          className="min-w-[12rem] flex-1 rounded border border-stone-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50"
        >
          Search
        </button>
        {search ? (
          <button
            type="button"
            className="rounded px-3 py-1.5 text-sm text-stone-600 hover:bg-stone-100"
            onClick={() => {
              setSearchInput("");
              setSearch("");
              setPage(0);
            }}
          >
            Clear
          </button>
        ) : null}
      </form>

      {membersQ.isLoading && !membersQ.data ? (
        <p className="mt-3 text-sm text-stone-500">Loading rows…</p>
      ) : membersQ.isError ? (
        <p className="mt-3 text-sm text-red-700">{(membersQ.error as Error).message}</p>
      ) : (
        <>
          <ul className="mt-3 max-h-[32rem] divide-y divide-stone-100 overflow-y-auto rounded border border-stone-200">
            {(membersQ.data?.items ?? []).map((row) => (
              <li key={row.id} className="px-3 py-2 text-sm">
                <Link
                  className="font-medium text-indigo-700 hover:underline"
                  to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.id}`}
                >
                  {row.display_label}
                </Link>
                <p className="mt-0.5 font-mono text-[10px] text-stone-500">{row.entity_key.split(":").pop()}</p>
              </li>
            ))}
            {(membersQ.data?.items.length ?? 0) === 0 ? (
              <li className="px-3 py-6 text-center text-sm text-stone-500">
                {search ? "No rows match this filter." : "No canon rows linked to this database yet."}
              </li>
            ) : null}
          </ul>

          {pageInfo.total > PAGE_SIZE ? (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-stone-600">
              <span>
                {pageInfo.start}–{pageInfo.end} of {pageInfo.total.toLocaleString()}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-stone-300 bg-white px-3 py-1 text-sm disabled:opacity-40"
                  disabled={page === 0 || membersQ.isFetching}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="rounded border border-stone-300 bg-white px-3 py-1 text-sm disabled:opacity-40"
                  disabled={page + 1 >= pageInfo.pageCount || membersQ.isFetching}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
