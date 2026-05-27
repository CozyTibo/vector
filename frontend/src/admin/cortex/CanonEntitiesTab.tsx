import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CanonEntityDetail, CanonEntityItem } from "../cortexAdminTypes";

export default function CanonEntitiesTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [search, setSearch] = useState("");
  const listQ = useQuery({
    queryKey: ["admin-cortex-canon-entities", tenantId, search],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "30" });
      if (search.trim()) params.set("search", search.trim());
      return adminJson<{ items: CanonEntityItem[]; total_count: number }>(
        `/admin/tenants/${tenantId}/cortex/canon/entities?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  return (
    <div className="space-y-4">
      <input
        type="search"
        placeholder="Search label or entity key"
        className="w-full max-w-md rounded border border-stone-300 px-3 py-2 text-sm"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {listQ.isLoading ? (
        <p className="text-sm text-stone-500">Loading entities…</p>
      ) : (
        <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200">
          {(listQ.data?.items ?? []).map((e) => (
            <li key={e.id} className="px-4 py-3 text-sm">
              <Link
                to={`/admin/tenants/${tenantId}/cortex/canon/entities/${e.id}`}
                className="font-medium text-indigo-700 hover:underline"
              >
                {e.display_label}
              </Link>
              <span className="ml-2 text-stone-500">{e.entity_type}</span>
              <span className="block font-mono text-xs text-stone-400">{e.entity_key}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-stone-500">Total: {listQ.data?.total_count ?? 0}</p>
    </div>
  );
}

export function CanonEntityDetailView() {
  const { tenantId = "", entityId = "" } = useParams<{ tenantId: string; entityId: string }>();
  const detailQ = useQuery({
    queryKey: ["admin-cortex-canon-entity", tenantId, entityId],
    queryFn: () =>
      adminJson<CanonEntityDetail>(
        `/admin/tenants/${tenantId}/cortex/canon/entities/${entityId}`,
      ),
    enabled: Boolean(tenantId && entityId),
  });

  if (detailQ.isLoading) return <p className="text-sm text-stone-500">Loading…</p>;
  if (!detailQ.data) return <p className="text-sm text-red-700">Entity not found.</p>;
  const d = detailQ.data;

  return (
    <div className="space-y-4">
      <Link
        to={`/admin/tenants/${tenantId}/cortex/canon`}
        className="text-sm text-indigo-700 hover:underline"
      >
        ← Back to canon
      </Link>
      <h2 className="text-lg font-semibold">{d.display_label}</h2>
      <p className="font-mono text-xs text-stone-500">{d.entity_key}</p>
      <pre className="max-h-48 overflow-auto rounded bg-stone-50 p-3 text-xs">
        {JSON.stringify(d.attrs_json, null, 2)}
      </pre>
      <h3 className="font-semibold">Sources</h3>
      <ul className="space-y-2 text-sm">
        {d.sources.map((s) => (
          <li key={s.raw_id} className="rounded border border-stone-100 p-2">
            raw_id {s.raw_id} · {s.resource_type} · {s.is_latest ? "latest" : "historical"}
            <pre className="mt-1 max-h-32 overflow-auto text-xs text-stone-600">
              {JSON.stringify(s.payload_preview, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
