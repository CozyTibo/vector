import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import AdminFeedbackBanner from "../ui/AdminFeedbackBanner";
import type { GraphEntityLinks } from "../cortexAdminTypes";

type EntityRebuildLinksResponse = {
  status: string;
  reason?: string | null;
  extractor_version?: number | null;
  error_summary?: string | null;
  stats: Record<string, number>;
};

type AdminFlash = { kind: "success" | "error"; message: string };

export function GraphEntityLinksPanel({ entityId }: { entityId: string }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [flash, setFlash] = useState<AdminFlash | null>(null);

  const q = useQuery({
    queryKey: ["admin-cortex-graph-entity-links", tenantId, entityId],
    queryFn: () =>
      adminJson<GraphEntityLinks>(
        `/admin/tenants/${tenantId}/cortex/graph/entities/${entityId}/links?limit=20`,
      ),
    enabled: Boolean(tenantId && entityId),
  });

  const rebuildM = useMutation({
    mutationFn: () =>
      adminJson<EntityRebuildLinksResponse>(
        `/admin/tenants/${tenantId}/cortex/graph/entities/${entityId}/actions/rebuild-links`,
        { method: "POST" },
      ),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-entity-links", tenantId, entityId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-graph-readiness", tenantId] });
      const stats = data.stats ?? {};
      if (data.status === "skipped") {
        setFlash({
          kind: "error",
          message:
            data.reason === "canon_backlog"
              ? "Rebuild skipped — canon backlog must clear before graph extract."
              : `Rebuild skipped (${data.reason ?? "unknown"}).`,
        });
        return;
      }
      if (data.status === "failed") {
        setFlash({
          kind: "error",
          message: data.error_summary ?? "Rebuild failed.",
        });
        return;
      }
      const upserted = stats.edges_upserted ?? 0;
      const unchanged = stats.edges_unchanged ?? 0;
      const unresolved = stats.unresolved_refs ?? 0;
      setFlash({
        kind: "success",
        message: `Links rebuilt (extractor v${data.extractor_version ?? "?"}). ${upserted} new, ${unchanged} unchanged, ${unresolved} unresolved.`,
      });
    },
    onError: (err: Error) => {
      setFlash({ kind: "error", message: err.message });
    },
  });

  if (q.isPending) return <p className="text-sm text-stone-500">Loading execution links…</p>;
  if (q.isError) return null;
  const outbound = q.data?.outbound ?? [];
  const inbound = q.data?.inbound ?? [];
  const hasLinks = outbound.length > 0 || inbound.length > 0;

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
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-stone-500">
          Re-runs graph extractors for this entity at the current extractor version.
        </p>
        <button
          type="button"
          className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
          disabled={rebuildM.isPending}
          onClick={() => {
            setFlash(null);
            rebuildM.mutate();
          }}
        >
          {rebuildM.isPending ? "Rebuilding…" : "Rebuild links"}
        </button>
      </div>
      {flash ? (
        <AdminFeedbackBanner
          kind={flash.kind}
          message={flash.message}
          onDismiss={() => setFlash(null)}
        />
      ) : null}
      {!hasLinks ? (
        <p className="text-sm text-stone-500">No projected execution links for this entity.</p>
      ) : null}
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
