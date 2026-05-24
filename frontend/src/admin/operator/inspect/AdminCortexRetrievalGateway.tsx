import { Navigate, useParams } from "react-router-dom";

import AdminCortexRetrievalPage from "../../AdminCortexRetrievalPage";
import { isCortexAdminV2Enabled } from "../featureFlags";

export default function AdminCortexRetrievalGateway() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  if (isCortexAdminV2Enabled()) {
    return <Navigate to={`/admin/tenants/${tenantId}/cortex/inspect/retrieval`} replace />;
  }
  return <AdminCortexRetrievalPage />;
}
