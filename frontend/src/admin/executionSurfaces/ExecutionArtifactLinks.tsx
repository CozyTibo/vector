import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { GraphEntityLinks } from "../cortexAdminTypes";
import { OmissionBanner } from "./OmissionBanner";

export function ExecutionArtifactLinks({ entityId }: { entityId: string }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["execution-surface-artifact-links", tenantId, entityId],
    queryFn: () =>
      adminJson<GraphEntityLinks>(
        `/admin/tenants/${tenantId}/cortex/graph/entities/${entityId}/links?limit=40`,
      ),
    enabled: Boolean(tenantId && entityId),
  });

  if (q.isPending) return <p className="text-sm text-stone-500">Loading graph links…</p>;
  if (q.isError) {
    return (
      <OmissionBanner
        omission={{
          code: "graph_links_unavailable",
          message: "Could not load graph links for this artifact.",
          remediation: "Check Graph lane health in Links tab.",
        }}
      />
    );
  }

  const outbound = q.data?.outbound ?? [];
  const inbound = q.data?.inbound ?? [];
  if (outbound.length === 0 && inbound.length === 0) {
    return (
      <OmissionBanner
        omission={{
          code: "no_graph_relationships",
          message: "No graph relationships found for this artifact.",
          remediation: "Improve graph extraction or rebuild links from substrate tab.",
        }}
      />
    );
  }

  const renderRow = (row: GraphEntityLinks["outbound"][number], direction: "out" | "in") => (
    <li key={row.id} className="border-b border-stone-100 py-2 text-sm">
      <span className="font-medium text-indigo-800">{row.relationship_kind_label}</span>
      <span className="text-stone-400"> · {row.confidence}</span>
      <p className="text-stone-700">
        {direction === "out" ? (
          <>
            →{" "}
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/work/${row.to.entity_id}`}
            >
              {row.to.display_label ?? row.to.entity_id}
            </Link>
          </>
        ) : (
          <>
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/work/${row.from.entity_id}`}
            >
              {row.from.display_label ?? row.from.entity_id}
            </Link>
            {" → this"}
          </>
        )}
      </p>
      <p className="font-mono text-xs text-stone-500">{row.extractor_rule}</p>
    </li>
  );

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div>
        <h4 className="text-sm font-medium text-stone-800">Outbound</h4>
        <ul>{outbound.map((row) => renderRow(row, "out"))}</ul>
      </div>
      <div>
        <h4 className="text-sm font-medium text-stone-800">Inbound</h4>
        <ul>{inbound.map((row) => renderRow(row, "in"))}</ul>
      </div>
    </div>
  );
}
