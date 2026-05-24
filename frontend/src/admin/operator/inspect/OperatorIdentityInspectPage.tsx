import { useNavigate, useParams } from "react-router-dom";

import { IdentityContinuityInspector } from "../../cortex/graph/IdentityContinuityInspector";
import { DeployInfoFooter } from "../DeployInfoFooter";

export default function OperatorIdentityInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Identity inspect</h1>
        <p className="mt-1 text-sm text-stone-600">
          Search resolves org entities from external keys. Entity cards show promotion lineage and evidence.
        </p>
      </header>

      <IdentityContinuityInspector
        lean
        onSelectEntity={(entityId) =>
          navigate(`/admin/tenants/${tenantId}/cortex/inspect/identity/e/${entityId}`)
        }
      />

      <DeployInfoFooter />
    </div>
  );
}
