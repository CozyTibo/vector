import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { GraphEntityLinks } from "../cortexAdminTypes";

export function GraphEntityLinksPanel({ entityId }: { entityId: string }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-graph-entity-links", tenantId, entityId],
    queryFn: () =>
      adminJson<GraphEntityLinks>(
        `/admin/tenants/${tenantId}/cortex/graph/entities/${entityId}/links?limit=20`,
      ),
    enabled: Boolean(tenantId && entityId),
  });

  if (q.isPending) return <p className="text-sm text-stone-500">Loading execution links…</p>;
  if (q.isError) return null;
  const outbound = q.data?.outbound ?? [];
  const inbound = q.data?.inbound ?? [];
  if (outbound.length === 0 && inbound.length === 0) {
    return <p className="text-sm text-stone-500">No projected execution links for this entity.</p>;
  }

  const renderRow = (row: GraphEntityLinks["outbound"][number], direction: "out" | "in") => (
    <li key={row.id} className="text-sm text-stone-700">
      <span className="font-medium text-indigo-800">{row.relationship_kind_label}</span>
      {" · "}
      {direction === "out" ? (
        <>
          this →{" "}
          <Link
            className="text-indigo-700 hover:underline"
            to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.to.entity_id}`}
          >
            {row.to.display_label ?? row.to.entity_id}
          </Link>
        </>
      ) : (
        <>
          <Link
            className="text-indigo-700 hover:underline"
            to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.from.entity_id}`}
          >
            {row.from.display_label ?? row.from.entity_id}
          </Link>
          {" → this"}
        </>
      )}
    </li>
  );

  return (
    <div className="space-y-3">
      {outbound.length > 0 ? (
        <div>
          <h4 className="text-xs font-semibold uppercase text-stone-500">Outbound</h4>
          <ul className="mt-1 list-disc space-y-1 pl-5">{outbound.map((r) => renderRow(r, "out"))}</ul>
        </div>
      ) : null}
      {inbound.length > 0 ? (
        <div>
          <h4 className="text-xs font-semibold uppercase text-stone-500">Inbound</h4>
          <ul className="mt-1 list-disc space-y-1 pl-5">{inbound.map((r) => renderRow(r, "in"))}</ul>
        </div>
      ) : null}
      <Link
        className="text-sm text-indigo-700 hover:underline"
        to={`/admin/tenants/${tenantId}/cortex/links?entity_id=${entityId}`}
      >
        View all in Links tab
      </Link>
    </div>
  );
}
