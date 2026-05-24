import { Navigate, useParams } from "react-router-dom";

import AdminCortexIdentityPage from "../../AdminCortexIdentityPage";
import { isCortexAdminV2Enabled } from "../featureFlags";

export default function AdminCortexIdentityGateway() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  if (isCortexAdminV2Enabled()) {
    return <Navigate to={`/admin/tenants/${tenantId}/cortex/inspect/identity`} replace />;
  }
  return <AdminCortexIdentityPage />;
}
