import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type Row = {
  id: number;
  replay_sequence: number;
  resource_type: string;
  external_id: string;
  fetched_at: string;
  http_status: number;
};

const PAGE = 80;

export default function AdminTenantStep1() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [page, setPage] = useState(0);
  const q = useQuery({
    queryKey: ["admin-raw", tenantId, page],
    queryFn: () =>
      adminJson<{ items: Row[]; total: number; limit: number; offset: number }>(
        `/admin/tenants/${tenantId}/raw-ingestion?limit=${PAGE}&offset=${page * PAGE}`,
      ),
    enabled: Boolean(tenantId),
  });

  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const maxPage = Math.max(0, Math.ceil(q.data.total / PAGE) - 1);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-sm disabled:opacity-40"
          disabled={page <= 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          Previous
        </button>
        <span className="text-sm text-stone-600">
          Page {page + 1} / {maxPage + 1} — {q.data.total} rows
        </span>
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-sm disabled:opacity-40"
          disabled={page >= maxPage}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="data-table text-xs">
          <thead>
            <tr>
              <th>replay_sequence</th>
              <th>resource_type</th>
              <th>external_id</th>
              <th>fetched_at</th>
              <th>http_status</th>
            </tr>
          </thead>
          <tbody>
            {q.data.items.map((r) => (
              <tr key={r.id}>
                <td>{r.replay_sequence}</td>
                <td>{r.resource_type}</td>
                <td className="max-w-[14rem] truncate font-mono">{r.external_id}</td>
                <td>{new Date(r.fetched_at).toLocaleString()}</td>
                <td>{r.http_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
