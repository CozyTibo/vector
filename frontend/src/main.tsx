import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AdminLayout from "./admin/AdminLayout.tsx";
import AdminCortexCanonicalLayout from "./admin/AdminCortexCanonicalLayout.tsx";
import AdminCortexInspectLayout from "./admin/operator/inspect/AdminCortexInspectLayout.tsx";
import InspectorHubPage from "./admin/operator/inspect/InspectorHubPage.tsx";
import OperatorGraphInspectPage from "./admin/operator/inspect/OperatorGraphInspectPage.tsx";
import OperatorIdentityEntityInspectPage from "./admin/operator/inspect/OperatorIdentityEntityInspectPage.tsx";
import OperatorIdentityInspectPage from "./admin/operator/inspect/OperatorIdentityInspectPage.tsx";
import OperatorExecutionInspectPage from "./admin/operator/inspect/OperatorExecutionInspectPage.tsx";
import OperatorRetrievalInspectPage from "./admin/operator/inspect/OperatorRetrievalInspectPage.tsx";
import OperatorRetrievalLineageInspectPage from "./admin/operator/inspect/OperatorRetrievalLineageInspectPage.tsx";
import OperatorSynthesisInspectPage from "./admin/operator/inspect/OperatorSynthesisInspectPage.tsx";
import OperatorIslandsInspectPage from "./admin/operator/inspect/OperatorIslandsInspectPage.tsx";
import OperatorPeoplePage from "./admin/operator/OperatorPeoplePage.tsx";
import OperatorPersonProfilePage from "./admin/operator/OperatorPersonProfilePage.tsx";
import OperatorOverviewPage from "./admin/operator/OperatorOverviewPage.tsx";
import OperatorRuntimePage from "./admin/operator/OperatorRuntimePage.tsx";
import OperatorQueuesPage from "./admin/operator/OperatorQueuesPage.tsx";
import OperatorCanonicalPage from "./admin/operator/OperatorCanonicalPage.tsx";
import AdminCortexIngestionPage from "./admin/AdminCortexIngestionPage.tsx";
import AdminCortexReasoningJobDetailPage from "./admin/AdminCortexReasoningJobDetailPage.tsx";
import AdminCortexSettingsPage from "./admin/AdminCortexSettingsPage.tsx";
import AdminCortexSynthesisJobDetailPage from "./admin/AdminCortexSynthesisJobDetailPage.tsx";
import AdminIntegrationsPage from "./admin/AdminIntegrationsPage.tsx";
import AdminTenantCortexLayout from "./admin/AdminTenantCortexLayout.tsx";
import AdminTenantOnboardingPage from "./admin/AdminTenantOnboardingPage.tsx";
import AdminTenantLayout from "./admin/AdminTenantLayout.tsx";
import AdminWorkspacePage from "./admin/AdminWorkspacePage.tsx";
import AdminUsersPage from "./admin/AdminUsersPage.tsx";
import AdminWorkspacesPage from "./admin/AdminWorkspacesPage.tsx";
import {
  RedirectTenantToIntegrations,
  RedirectTenantToWorkspace,
} from "./admin/adminRedirects.tsx";
import RequireAuth from "./layouts/RequireAuth.tsx";
import AppHomePage from "./pages/app/AppHomePage.tsx";
import AppTeamSpacePage from "./pages/app/AppTeamSpacePage.tsx";
import AppTeamsPage from "./pages/app/AppTeamsPage.tsx";
import OnboardingPage from "./pages/app/OnboardingPage.tsx";
import LandingPage from "./pages/LandingPage.tsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.tsx";
import LoginPage from "./pages/LoginPage.tsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.tsx";
import SignupPage from "./pages/SignupPage.tsx";
import SignupWaitlistPage from "./pages/SignupWaitlistPage.tsx";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function LegacyCortexRedirect({ to }: { to: string }) {
  return <Navigate to={to} replace />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/login/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/login/reset-password" element={<ResetPasswordPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/signup/waitlist" element={<SignupWaitlistPage />} />

          <Route element={<RequireAuth />}>
            <Route path="/app" element={<AppHomePage />} />
            <Route path="/app/teams/:teamId" element={<Navigate to="/app/access/:teamId" replace />} />
            <Route path="/app/teams" element={<Navigate to="/app/access" replace />} />
            <Route path="/app/access/:teamId" element={<AppTeamSpacePage />} />
            <Route path="/app/access" element={<AppTeamsPage />} />
            <Route path="/app/onboarding" element={<OnboardingPage />} />
            <Route path="/app/connectors" element={<Navigate to="/app" replace />} />
            <Route path="/app/github/ingestion" element={<Navigate to="/app" replace />} />
          </Route>

          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminWorkspacesPage />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="workspaces" element={<Navigate to="/admin" replace />} />
            <Route path="manager-onboarding" element={<Navigate to="/admin" replace />} />
            <Route path="slack-onboarding" element={<Navigate to="/admin" replace />} />
            <Route path="manager-onboarding/sessions/:sessionId" element={<Navigate to="/admin" replace />} />
            <Route path="tenants/:tenantId" element={<AdminTenantLayout />}>
              <Route index element={<Navigate to="workspace" replace />} />
              <Route path="workspace" element={<AdminWorkspacePage />} />
              <Route path="onboarding" element={<AdminTenantOnboardingPage />} />
              <Route path="overview" element={<RedirectTenantToWorkspace />} />
              <Route path="integrations" element={<AdminIntegrationsPage />} />
              <Route path="cortex-ingestion" element={<Navigate to="../cortex/ingestion" replace />} />
              <Route path="cortex" element={<AdminTenantCortexLayout />}>
                <Route index element={<Navigate to="overview" replace />} />
                <Route path="overview" element={<OperatorOverviewPage />} />
                <Route path="runtime" element={<OperatorRuntimePage />} />
                <Route path="queues" element={<OperatorQueuesPage />} />
                <Route path="people" element={<OperatorPeoplePage />} />
                <Route path="people/:personId" element={<OperatorPersonProfilePage />} />
                <Route path="ingestion" element={<AdminCortexIngestionPage />} />
                <Route path="canonical" element={<AdminCortexCanonicalLayout />}>
                  <Route index element={<OperatorCanonicalPage />} />
                  <Route path="health" element={<Navigate to=".." replace />} />
                </Route>
                <Route path="inspect" element={<AdminCortexInspectLayout />}>
                  <Route index element={<InspectorHubPage />} />
                  <Route path="identity" element={<OperatorIdentityInspectPage />} />
                  <Route path="identity/e/:entityId" element={<OperatorIdentityEntityInspectPage />} />
                  <Route path="graph" element={<OperatorGraphInspectPage />} />
                  <Route path="islands" element={<OperatorIslandsInspectPage />} />
                  <Route path="retrieval" element={<OperatorRetrievalInspectPage />} />
                  <Route path="retrieval/lineage" element={<OperatorRetrievalLineageInspectPage />} />
                  <Route path="synthesis" element={<OperatorSynthesisInspectPage />} />
                  <Route path="execution" element={<OperatorExecutionInspectPage />} />
                </Route>
                <Route path="settings" element={<AdminCortexSettingsPage />} />
                <Route path="identity" element={<LegacyCortexRedirect to="../inspect/identity" />} />
                <Route path="graph" element={<LegacyCortexRedirect to="../inspect/graph" />} />
                <Route path="reconstruction" element={<LegacyCortexRedirect to="../inspect/execution" />} />
                <Route path="reconstruction/jobs/:jobId" element={<AdminCortexReasoningJobDetailPage />} />
                <Route path="retrieval" element={<LegacyCortexRedirect to="../inspect/retrieval" />} />
                <Route path="synthesis" element={<LegacyCortexRedirect to="../inspect/synthesis" />} />
                <Route path="synthesis/jobs/:jobId" element={<AdminCortexSynthesisJobDetailPage />} />
                <Route path="entity-resolution" element={<Navigate to="../inspect/identity" replace />} />
                <Route path="identity-certification" element={<Navigate to="../inspect/identity" replace />} />
                <Route path="identity/*" element={<Navigate to="../inspect/identity" replace />} />
                <Route path="traversal" element={<Navigate to="../inspect/graph" replace />} />
                <Route path="traversal/*" element={<Navigate to="../../inspect/graph" replace />} />
                <Route path="memory" element={<Navigate to="../overview" replace />} />
                <Route path="reasoning" element={<Navigate to="../inspect/execution" replace />} />
                <Route path="reasoning/*" element={<Navigate to="../../inspect/execution" replace />} />
                <Route path="verification" element={<Navigate to="../overview" replace />} />
                <Route path="settings-debug" element={<Navigate to="../settings" replace />} />
              </Route>
              <Route path="connections" element={<RedirectTenantToIntegrations />} />
              <Route path="slack-onboarding" element={<RedirectTenantToWorkspace />} />
              <Route path="manager-onboarding" element={<RedirectTenantToWorkspace />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
