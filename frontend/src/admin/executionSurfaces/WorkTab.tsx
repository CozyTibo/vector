import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "../cortex/CortexPageSkeleton";
import { ExecutionArtifactLinks } from "./ExecutionArtifactLinks";
import { ObservationFootnote, OmissionBanner } from "./OmissionBanner";

export function WorkTab() {
  const { tenantId = "", artifactId: artifactIdParam } = useParams<{ tenantId: string; artifactId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const artifactId = artifactIdParam ?? searchParams.get("artifact_id");
  const entityType = searchParams.get("entity_type") ?? "";

  const listQ = useQuery({
    queryKey: ["execution-surface-work", tenantId, entityType],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "80" });
      if (entityType) params.set("entity_type", entityType);
      return adminJson<{ items: Array<Record<string, unknown>> }>(
        `/admin/tenants/${tenantId}/cortex/execution-surfaces/work?${params}`,
      );
    },
    enabled: !artifactId,
  });

  const detailQ = useQuery({
    queryKey: ["execution-surface-work-detail", tenantId, artifactId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/execution-surfaces/work/${artifactId}`,
      ),
    enabled: Boolean(artifactId),
  });

  if (artifactId) {
    if (detailQ.isLoading) return <CortexPageSkeleton label="Loading artifact" />;
    const d = detailQ.data;
    if (!d) return null;
    const entity = (d.entity ?? {}) as Record<string, unknown>;
    const discussions = (d.discussions ?? {}) as {
      omission?: { code: string; message: string; remediation: string | null };
    };
    return (
      <div className="space-y-4">
        <Link
          to={`/admin/tenants/${tenantId}/cortex/execution-surfaces?tab=work`}
          className="text-sm text-indigo-700 hover:underline"
        >
          ← All work
        </Link>
        <h2 className="text-xl font-semibold">{String(entity.display_label)}</h2>
        <p className="text-sm text-stone-600">
          {String(entity.entity_type)} · {String(entity.connector)}
          {entity.provider_status ? ` · ${String(entity.provider_status)}` : ""}
        </p>
        <ObservationFootnote text={String((d.activity as Record<string, unknown>)?.footnote ?? "")} />
        <section className="rounded-xl border border-stone-200 bg-white p-4">
          <h3 className="font-semibold">Domain membership</h3>
          <ul className="mt-2 text-sm">
            {((d.domain_memberships ?? []) as Array<Record<string, unknown>>).map((dm) => (
              <li key={String(dm.id)} className="py-1">
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/domains/${dm.id}`}
                  className="text-indigo-800 hover:underline"
                >
                  {String(dm.display_name)}
                </Link>
                <p className="font-mono text-xs text-stone-500">
                  {String((dm.membership as Record<string, unknown>)?.extractor_rule ?? "")}
                </p>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl border border-stone-200 bg-white p-4">
          <h3 className="font-semibold">Connected artifacts</h3>
          <ExecutionArtifactLinks entityId={String(entity.canon_entity_id)} />
        </section>
        <section className="rounded-xl border border-stone-200 bg-white p-4">
          <h3 className="font-semibold">Discussions</h3>
          <OmissionBanner omission={discussions.omission ?? null} />
        </section>
      </div>
    );
  }

  if (listQ.isLoading) return <CortexPageSkeleton label="Loading work" />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {(["", "work_item", "pull_request", "document", "deployment"] as const).map((t) => (
          <button
            key={t || "all"}
            type="button"
            className={`rounded px-2 py-1 text-sm ${
              entityType === t ? "bg-indigo-100 text-indigo-900" : "bg-stone-100"
            }`}
            onClick={() =>
              setSearchParams((prev) => {
                const p = new URLSearchParams(prev);
                p.set("tab", "work");
                if (t) p.set("entity_type", t);
                else p.delete("entity_type");
                return p;
              })
            }
          >
            {t || "all"}
          </button>
        ))}
      </div>
      <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
        {(listQ.data?.items ?? []).map((row) => (
          <li key={String(row.canon_entity_id)} className="px-4 py-3 text-sm">
            <Link
              to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/work/${row.canon_entity_id}`}
              className="font-medium text-indigo-800 hover:underline"
            >
              {String(row.display_label)}
            </Link>
            <p className="text-xs text-stone-500">
              {String(row.entity_type)} · {String(row.connector)}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
