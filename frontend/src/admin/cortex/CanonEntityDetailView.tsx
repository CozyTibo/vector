import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CanonEntityDetail } from "../cortexAdminTypes";

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
        to={`/admin/tenants/${tenantId}/cortex/canon?tab=entities`}
        className="text-sm text-indigo-700 hover:underline"
      >
        ← Back to canonical entities
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
