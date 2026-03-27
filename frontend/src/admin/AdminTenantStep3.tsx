import { useParams } from "react-router-dom";

import CanonicalDebugPage from "../pages/debug/CanonicalDebugPage";
import { adminCanonicalClient } from "../lib/canonicalApi";
import { getAdminPassword } from "../lib/adminCredentials";

export default function AdminTenantStep3() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const pw = getAdminPassword();
  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant</p>;
  }
  if (!pw) {
    return <p className="text-sm text-red-700">Admin session missing.</p>;
  }
  return (
    <CanonicalDebugPage
      client={adminCanonicalClient(tenantId, pw)}
      entityBasePath={`/admin/tenants/${tenantId}/step3`}
      dashboardHref="/admin"
      visualTheme="admin"
    />
  );
}
