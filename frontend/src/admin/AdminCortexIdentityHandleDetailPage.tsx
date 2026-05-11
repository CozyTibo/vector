import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import type { CortexOrgEntityItem } from "./cortexAdminTypes";

export default function AdminCortexIdentityHandleDetailPage() {
  const { tenantId = "", handleId = "" } = useParams<{ tenantId: string; handleId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-identity-handle-detail", tenantId, handleId],
    queryFn: () =>
      adminJson<CortexOrgEntityItem>(`/admin/tenants/${tenantId}/cortex/identity/handles/${handleId}`),
    enabled: Boolean(tenantId && handleId),
  });

  if (!tenantId || !handleId) return <p className="text-sm text-red-700">Missing tenant or handle id.</p>;
  if (q.isPending) return <p className="text-sm text-stone-600">Loading handle…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;

  const e = q.data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Phase 04</p>
          <h1 className="mt-1 text-xl font-semibold text-stone-900">Org handle detail</h1>
          <p className="mt-1 font-mono text-xs text-stone-500">{String(e.id)}</p>
        </div>
        <div className="flex flex-wrap gap-3 text-sm">
          <Link
            to={`/admin/tenants/${tenantId}/cortex/identity/handles`}
            className="font-medium text-indigo-700 hover:text-indigo-900"
          >
            ← All handles
          </Link>
          <Link
            to={`/admin/tenants/${tenantId}/cortex/entity-resolution`}
            className="font-medium text-stone-600 hover:text-stone-900"
          >
            Overview
          </Link>
        </div>
      </div>

      <dl className="grid gap-2 rounded-lg border border-stone-200 bg-white p-4 text-sm sm:grid-cols-2">
        <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Entity kind</dt>
        <dd className="font-mono text-stone-900">{e.entity_kind}</dd>
        <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Lifecycle</dt>
        <dd className="font-mono text-stone-900">{e.lifecycle_state}</dd>
        <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Fingerprint</dt>
        <dd className="break-all font-mono text-xs text-stone-800">{e.identity_key_fingerprint}</dd>
        <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">Engine</dt>
        <dd className="font-mono text-xs text-stone-800">{e.engine_build_ref}</dd>
      </dl>

      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">metadata_json</p>
        <pre className="mt-1 max-h-[50vh] overflow-auto rounded-lg border border-stone-200 bg-stone-50 p-3 text-xs text-stone-800">
          {JSON.stringify(e.metadata_json ?? {}, null, 2)}
        </pre>
      </div>
    </div>
  );
}
