import { Navigate, useParams } from "react-router-dom";

import AdminCortexSynthesisPage from "../../AdminCortexSynthesisPage";
import { isCortexAdminV2Enabled } from "../featureFlags";

export default function AdminCortexSynthesisGateway() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  if (isCortexAdminV2Enabled()) {
    return <Navigate to={`/admin/tenants/${tenantId}/cortex/inspect/synthesis`} replace />;
  }
  return <AdminCortexSynthesisPage />;
}
