import { Link, useParams } from "react-router-dom";

import { IdentityEntityCard } from "../../cortex/graph/IdentityEntityCard";
import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { useIdentityContinuityEntity } from "../../cortex/graph/useIdentityContinuityInspector";
import { DeployInfoFooter } from "../DeployInfoFooter";

export default function OperatorIdentityEntityInspectPage() {
  const { tenantId = "", entityId = "" } = useParams<{ tenantId: string; entityId: string }>();
  const entityQ = useIdentityContinuityEntity(entityId || null);

  if (!entityId) {
    return <p className="text-sm text-red-700">Missing entity id.</p>;
  }

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <Link
          to={`/admin/tenants/${tenantId}/cortex/inspect/identity`}
          className="text-xs font-medium text-indigo-700 no-underline hover:underline"
        >
          ← Back to identity search
        </Link>
        <h1 className="mt-2 text-lg font-semibold text-stone-900">Entity continuity</h1>
        <p className="mt-1 font-mono text-xs text-stone-600">{entityId}</p>
      </header>

      {entityQ.isPending && !entityQ.data ? (
        <SectionSkeleton variant="cards" />
      ) : entityQ.isError ? (
        <p className="text-sm text-red-700">{(entityQ.error as Error).message}</p>
      ) : entityQ.data ? (
        <IdentityEntityCard data={entityQ.data} />
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
