import { Navigate, useParams } from "react-router-dom";

import AdminCortexGraphPage from "../../AdminCortexGraphPage";
import { isCortexAdminV2Enabled } from "../featureFlags";

export default function AdminCortexGraphGateway() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  if (isCortexAdminV2Enabled()) {
    return <Navigate to={`/admin/tenants/${tenantId}/cortex/inspect/graph`} replace />;
  }
  return <AdminCortexGraphPage />;
}
