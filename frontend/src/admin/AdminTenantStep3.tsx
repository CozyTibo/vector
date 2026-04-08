import { Navigate, useParams } from "react-router-dom";

/** @deprecated Route preserved; UI lives on execution-graph. */
export default function AdminTenantStep3() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph`} replace />;
}
