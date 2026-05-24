import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { CanonicalHealthStrip } from "../canonical/CanonicalHealthStrip";
import type { CortexCanonicalControlPlane } from "../cortexAdminTypes";
import { SectionSkeleton } from "../cortex/SectionSkeleton";
import { DeployInfoFooter } from "./DeployInfoFooter";

export default function OperatorCanonicalPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const controlPlaneQ = useQuery({
    queryKey: ["cortex-canonical-control-plane", tenantId],
    queryFn: () =>
      adminJson<CortexCanonicalControlPlane>(
        `/admin/tenants/${tenantId}/cortex/canonical/control-plane`,
      ),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      {controlPlaneQ.isPending && !controlPlaneQ.data ? (
        <SectionSkeleton variant="cards" />
      ) : controlPlaneQ.isError ? (
        <p className="text-sm text-red-700">{(controlPlaneQ.error as Error).message}</p>
      ) : controlPlaneQ.data ? (
        <CanonicalHealthStrip c={controlPlaneQ.data} />
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-white p-5 text-sm text-stone-700 shadow-sm">
        <p>
          Canonical deferrals and retry-ready materialization backlog live on{" "}
          <Link
            to={`/admin/tenants/${tenantId}/cortex/queues?tab=deferrals`}
            className="font-medium text-indigo-700 no-underline hover:underline"
          >
            Queues
          </Link>
          . Execution lease and phase receipts are on{" "}
          <Link
            to={`/admin/tenants/${tenantId}/cortex/runtime`}
            className="font-medium text-indigo-700 no-underline hover:underline"
          >
            Runtime
          </Link>
          .
        </p>
      </section>

      <DeployInfoFooter />
    </div>
  );
}