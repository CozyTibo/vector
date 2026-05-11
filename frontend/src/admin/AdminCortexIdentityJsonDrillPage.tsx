import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type Props = {
  title: string;
  /** Path segment after ``/cortex/identity/`` (e.g. ``links``, ``merge-queue``). */
  apiSuffix: string;
};

function JsonDrillInner({ title, apiSuffix }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { search } = useLocation();
  const q = useQuery({
    queryKey: ["admin-cortex-identity-json-drill", tenantId, apiSuffix, search],
    queryFn: () =>
      adminJson<unknown>(`/admin/tenants/${tenantId}/cortex/identity/${apiSuffix}${search}`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (q.isPending) return <p className="text-sm text-stone-600">Loading…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Phase 04</p>
          <h1 className="mt-1 text-xl font-semibold text-stone-900">{title}</h1>
          <p className="mt-1 font-mono text-xs text-stone-500">
            GET /admin/tenants/{"{tenant}"}/cortex/identity/{apiSuffix}
            {search || ""}
          </p>
        </div>
        <Link
          to={`/admin/tenants/${tenantId}/cortex/entity-resolution`}
          className="text-sm font-medium text-indigo-700 hover:text-indigo-900"
        >
          ← Identity overview
        </Link>
      </div>
      <pre className="max-h-[70vh] overflow-auto rounded-lg border border-stone-200 bg-stone-50 p-4 text-xs leading-relaxed text-stone-800">
        {JSON.stringify(q.data, null, 2)}
      </pre>
    </div>
  );
}

export function AdminCortexIdentityLinksDrillPage() {
  return <JsonDrillInner title="Org links" apiSuffix="links" />;
}

export function AdminCortexIdentityLinkCandidatesDrillPage() {
  return <JsonDrillInner title="Link candidates" apiSuffix="link-candidates" />;
}

export function AdminCortexIdentityMergeQueueDrillPage() {
  return <JsonDrillInner title="Merge queue" apiSuffix="merge-queue" />;
}

export function AdminCortexIdentityAmbiguityQueueDrillPage() {
  return <JsonDrillInner title="Ambiguity queue" apiSuffix="ambiguity-queue" />;
}

export function AdminCortexIdentityReplayJobsDrillPage() {
  return <JsonDrillInner title="Replay jobs" apiSuffix="replay-jobs" />;
}

export function AdminCortexIdentityBundleEquivalenceDrillPage() {
  return <JsonDrillInner title="Bundle equivalence" apiSuffix="bundle-equivalence" />;
}

export function AdminCortexIdentityPrimitivesDrillPage() {
  return <JsonDrillInner title="Primitives" apiSuffix="primitives" />;
}
