import { Navigate, useParams } from "react-router-dom";

export function RedirectTenantToWorkspace() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/workspace`} replace />;
}

export function RedirectTenantToIntegrations() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/integrations`} replace />;
}

export function RedirectStep1ToDataPipeline() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/data-pipeline?focus=raw`} replace />;
}

export function RedirectStep2ToDataPipeline() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/data-pipeline?focus=projections`} replace />;
}

export function RedirectStep3Artifact() {
  const { tenantId, artifactId } = useParams<{ tenantId: string; artifactId: string }>();
  return (
    <Navigate
      to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph/artifacts/${artifactId}`}
      replace
    />
  );
}

export function RedirectStep3Actor() {
  const { tenantId, actorId } = useParams<{ tenantId: string; actorId: string }>();
  return (
    <Navigate
      to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph/actors/${actorId}`}
      replace
    />
  );
}

/** Old URL: /tenants/:id/execution-graph/... → nested under data-pipeline. */
export function LegacyExecutionGraphRedirect() {
  const { tenantId, "*": star } = useParams<{ tenantId: string; "*": string }>();
  const extra = (star ?? "").replace(/^\/+|\/+$/g, "");
  const suffix = extra ? `/${extra}` : "";
  return (
    <Navigate
      to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph${suffix}`}
      replace
    />
  );
}

export function LegacyTenantDebugRedirect() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/data-pipeline/debug`} replace />;
}
