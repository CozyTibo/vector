import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type Conn = { id: string; provider: string; status: string; created_at: string };

const ENTITIES = ["repositories", "pull_requests", "commits", "issues", "users"] as const;

export default function AdminTenantStep2() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [entity, setEntity] = useState<(typeof ENTITIES)[number]>("repositories");
  const [page, setPage] = useState(0);
  const limit = 50;

  const conns = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  const githubConnId = useMemo(() => {
    const g = conns.data?.items.find((c) => c.provider === "github");
    return g?.id ?? "";
  }, [conns.data?.items]);

  const rows = useQuery({
    queryKey: ["admin-projections", tenantId, githubConnId, entity, page],
    queryFn: () =>
      adminJson<{ items: Record<string, unknown>[]; total: number }>(
        `/admin/tenants/${tenantId}/projections/github/${githubConnId}/rows?entity=${entity}&limit=${limit}&offset=${page * limit}`,
      ),
    enabled: Boolean(tenantId && githubConnId),
  });

  if (conns.isPending) {
    return <p className="text-sm text-stone-600">Loading connections…</p>;
  }
  if (conns.isError) {
    return <p className="text-sm text-red-700">{(conns.error as Error).message}</p>;
  }

  if (!githubConnId) {
    return (
      <p className="text-sm text-stone-600">
        No GitHub connection for this tenant — connect GitHub in the product UI first.
      </p>
    );
  }

  const table = ENTITIES.map((e) => (
    <button
      key={e}
      type="button"
      className={`rounded px-2 py-1 text-xs font-medium ${
        entity === e ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-800"
      }`}
      onClick={() => {
        setEntity(e);
        setPage(0);
      }}
    >
      {e}
    </button>
  ));

  return (
    <div>
      <p className="mb-2 font-mono text-xs text-stone-600">connection_id: {githubConnId}</p>
      <div className="mb-4 flex flex-wrap gap-2">{table}</div>
      {rows.isPending ? <p className="text-sm text-stone-600">Loading rows…</p> : null}
      {rows.isError ? (
        <p className="text-sm text-red-700">{(rows.error as Error).message}</p>
      ) : null}
      {rows.data ? (
        <>
          <div className="mb-2 flex gap-2 text-sm">
            <button
              type="button"
              className="rounded border border-stone-300 px-2 py-1 disabled:opacity-40"
              disabled={page <= 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Prev
            </button>
            <button
              type="button"
              className="rounded border border-stone-300 px-2 py-1 disabled:opacity-40"
              disabled={(page + 1) * limit >= rows.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
            <span className="text-stone-600">
              {rows.data.total} rows total — page {page + 1}
            </span>
          </div>
          <ProjectionTable items={rows.data.items} />
        </>
      ) : null}
    </div>
  );
}

function ProjectionTable({ items }: { items: Record<string, unknown>[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-stone-500">No rows</p>;
  }
  const keys = Object.keys(items[0] ?? {}).slice(0, 12);
  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
      <table className="data-table text-xs">
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((row, i) => (
            <tr key={i}>
              {keys.map((k) => (
                <td key={k} className="max-w-[12rem] truncate">
                  {formatCell(row[k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) {
    return "—";
  }
  if (typeof v === "object") {
    return JSON.stringify(v).slice(0, 80);
  }
  return String(v);
}
