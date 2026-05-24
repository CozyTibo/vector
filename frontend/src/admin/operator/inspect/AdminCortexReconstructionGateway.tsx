import { Navigate, useParams } from "react-router-dom";

import AdminCortexReconstructionPage from "../../AdminCortexReconstructionPage";
import { isCortexAdminV2Enabled } from "../featureFlags";

export default function AdminCortexReconstructionGateway() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  if (isCortexAdminV2Enabled()) {
    return <Navigate to={`/admin/tenants/${tenantId}/cortex/inspect/execution`} replace />;
  }
  return <AdminCortexReconstructionPage />;
}
