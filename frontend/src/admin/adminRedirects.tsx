import { Navigate, useParams } from "react-router-dom";

export function RedirectTenantToWorkspace() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/workspace`} replace />;
}

export function RedirectTenantToIntegrations() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/integrations`} replace />;
}
