import { useQuery } from "@tanstack/react-query";
import { Navigate, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

export function RedirectTenantToWorkspace() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/workspace`} replace />;
}

export function RedirectTenantToIntegrations() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/integrations`} replace />;
}

export function RedirectTenantToSlackOnboarding() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/admin/tenants/${tenantId}/slack-onboarding`} replace />;
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

/** Old URL: /admin/manager-onboarding/sessions/:id → tenant Slack onboarding hub. */
export function RedirectManagerOnboardingSessionToTenant() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const q = useQuery({
    queryKey: ["admin-mo-session-redirect", sessionId],
    queryFn: () => adminJson<{ tenant_id: string }>(`/admin/manager-onboarding/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
    retry: false,
  });
  if (!sessionId) {
    return <Navigate to="/admin" replace />;
  }
  if (q.isPending) {
    return <p className="mx-auto max-w-6xl px-4 py-6 text-sm text-stone-600">Loading session…</p>;
  }
  const tid = q.data?.tenant_id;
  if (tid) {
    return <Navigate to={`/admin/tenants/${tid}/slack-onboarding`} replace />;
  }
  return <Navigate to="/admin" replace />;
}
