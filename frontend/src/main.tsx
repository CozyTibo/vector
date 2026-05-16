import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AdminLayout from "./admin/AdminLayout.tsx";
import AdminCortexIdentityCertificationPage from "./admin/AdminCortexIdentityCertificationPage.tsx";
import AdminCortexIdentityHandleDetailPage from "./admin/AdminCortexIdentityHandleDetailPage.tsx";
import AdminCortexIdentityHandlesPage from "./admin/AdminCortexIdentityHandlesPage.tsx";
import {
  AdminCortexIdentityAmbiguityQueueDrillPage,
  AdminCortexIdentityBundleEquivalenceDrillPage,
  AdminCortexIdentityLinkCandidatesDrillPage,
  AdminCortexIdentityLinksDrillPage,
  AdminCortexIdentityMergeQueueDrillPage,
  AdminCortexIdentityPrimitivesDrillPage,
  AdminCortexIdentityReplayJobsDrillPage,
} from "./admin/AdminCortexIdentityJsonDrillPage.tsx";
import AdminCortexIdentityOverviewPage from "./admin/AdminCortexIdentityOverviewPage.tsx";
import AdminCortexIngestionPage from "./admin/AdminCortexIngestionPage.tsx";
import AdminCortexMemoryPage from "./admin/AdminCortexMemoryPage.tsx";
import AdminCortexOverviewPage from "./admin/AdminCortexOverviewPage.tsx";
import AdminCortexPlaceholderPage from "./admin/AdminCortexPlaceholderPage.tsx";
import AdminCortexReasoningCertificationPackPage from "./admin/AdminCortexReasoningCertificationPackPage.tsx";
import AdminCortexReasoningJobDetailPage from "./admin/AdminCortexReasoningJobDetailPage.tsx";
import AdminCortexReasoningJobsPage from "./admin/AdminCortexReasoningJobsPage.tsx";
import AdminCortexReasoningLayout from "./admin/AdminCortexReasoningLayout.tsx";
import AdminCortexReasoningLegalityPage from "./admin/AdminCortexReasoningLegalityPage.tsx";
import AdminCortexReasoningOverviewPage from "./admin/AdminCortexReasoningOverviewPage.tsx";
import AdminCortexRetrievalContinuityPage from "./admin/AdminCortexRetrievalContinuityPage.tsx";
import AdminCortexRetrievalLayout from "./admin/AdminCortexRetrievalLayout.tsx";
import AdminCortexRetrievalLegalityPage from "./admin/AdminCortexRetrievalLegalityPage.tsx";
import AdminCortexRetrievalLineagePage from "./admin/AdminCortexRetrievalLineagePage.tsx";
import AdminCortexRetrievalOverviewPage from "./admin/AdminCortexRetrievalOverviewPage.tsx";
import AdminCortexTraversalControlPlanePage from "./admin/AdminCortexTraversalControlPlanePage.tsx";
import AdminCortexTraversalLayout from "./admin/AdminCortexTraversalLayout.tsx";
import AdminCortexTraversalOverviewPage from "./admin/AdminCortexTraversalOverviewPage.tsx";
import AdminCortexCanonicalAmbiguitiesPage from "./admin/AdminCortexCanonicalAmbiguitiesPage.tsx";
import AdminCortexCanonicalCertificationPage from "./admin/AdminCortexCanonicalCertificationPage.tsx";
import AdminCortexCanonicalCoveragePage from "./admin/AdminCortexCanonicalCoveragePage.tsx";
import AdminCortexCanonicalControlPlanePage from "./admin/AdminCortexCanonicalControlPlanePage.tsx";
import AdminCortexCanonicalDebugTabPage from "./admin/AdminCortexCanonicalDebugTabPage.tsx";
import AdminCortexCanonicalDoctrineTabPage from "./admin/AdminCortexCanonicalDoctrineTabPage.tsx";
import AdminCortexCanonicalLayout from "./admin/AdminCortexCanonicalLayout.tsx";
import AdminCortexCanonicalLegacyOntologyToolsPage from "./admin/AdminCortexCanonicalLegacyOntologyToolsPage.tsx";
import AdminCortexCanonicalAdvancedLayout from "./admin/AdminCortexCanonicalAdvancedLayout.tsx";
import AdminCortexCanonicalFailuresPage from "./admin/AdminCortexCanonicalFailuresPage.tsx";
import AdminCortexCanonicalHealthPage from "./admin/AdminCortexCanonicalHealthPage.tsx";
import AdminCortexCanonicalRegistryPage from "./admin/AdminCortexCanonicalRegistryPage.tsx";
import AdminCortexCanonicalReplayTabPage from "./admin/AdminCortexCanonicalReplayTabPage.tsx";
import AdminCortexCanonicalRuntimePage from "./admin/AdminCortexCanonicalRuntimePage.tsx";
import AdminCortexCanonicalStabilizationPage from "./admin/AdminCortexCanonicalStabilizationPage.tsx";
import AdminCortexCanonicalVerificationTabPage from "./admin/AdminCortexCanonicalVerificationTabPage.tsx";
import AdminCortexGraphPage from "./admin/AdminCortexGraphPage.tsx";
import AdminCortexVerificationPage from "./admin/AdminCortexVerificationPage.tsx";
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
                <Route path="overview" element={<AdminCortexOverviewPage />} />
                <Route path="ingestion" element={<AdminCortexIngestionPage />} />
                <Route path="canonical" element={<AdminCortexCanonicalLayout />}>
                  <Route index element={<Navigate to="health" replace />} />
                  <Route path="health" element={<AdminCortexCanonicalHealthPage />} />
                  <Route path="coverage" element={<AdminCortexCanonicalCoveragePage />} />
                  <Route path="failures" element={<AdminCortexCanonicalFailuresPage />} />
                  <Route path="advanced" element={<AdminCortexCanonicalAdvancedLayout />}>
                    <Route index element={<Navigate to="runtime" replace />} />
                    <Route path="runtime" element={<AdminCortexCanonicalRuntimePage />} />
                    <Route path="replay" element={<AdminCortexCanonicalReplayTabPage />} />
                    <Route path="verification" element={<AdminCortexCanonicalVerificationTabPage />} />
                    <Route path="ambiguities" element={<AdminCortexCanonicalAmbiguitiesPage />} />
                    <Route path="registry" element={<AdminCortexCanonicalRegistryPage />} />
                    <Route path="doctrine" element={<AdminCortexCanonicalDoctrineTabPage />} />
                    <Route path="debug" element={<AdminCortexCanonicalDebugTabPage />} />
                    <Route path="legacy-tools" element={<AdminCortexCanonicalLegacyOntologyToolsPage />} />
                    <Route path="inspector" element={<AdminCortexCanonicalControlPlanePage />} />
                    <Route path="stabilization" element={<AdminCortexCanonicalStabilizationPage />} />
                    <Route path="certification" element={<AdminCortexCanonicalCertificationPage />} />
                  </Route>
                  <Route path="overview" element={<Navigate to="health" replace />} />
                  <Route path="runtime" element={<Navigate to="advanced/runtime" replace />} />
                  <Route path="replay" element={<Navigate to="advanced/replay" replace />} />
                  <Route path="verification" element={<Navigate to="advanced/verification" replace />} />
                  <Route path="ambiguities" element={<Navigate to="advanced/ambiguities" replace />} />
                  <Route path="registry" element={<Navigate to="advanced/registry" replace />} />
                  <Route path="doctrine" element={<Navigate to="advanced/doctrine" replace />} />
                  <Route path="debug" element={<Navigate to="advanced/debug" replace />} />
                  <Route path="legacy-tools" element={<Navigate to="advanced/legacy-tools" replace />} />
                  <Route path="inspector" element={<Navigate to="advanced/inspector" replace />} />
                  <Route path="stabilization" element={<Navigate to="advanced/stabilization" replace />} />
                  <Route path="certification" element={<Navigate to="advanced/certification" replace />} />
                  <Route path="control-plane" element={<Navigate to="health" replace />} />
                </Route>
                <Route path="entity-resolution" element={<AdminCortexIdentityOverviewPage />} />
                <Route path="identity-certification" element={<AdminCortexIdentityCertificationPage />} />
                <Route path="identity/handles/:handleId" element={<AdminCortexIdentityHandleDetailPage />} />
                <Route path="identity/handles" element={<AdminCortexIdentityHandlesPage />} />
                <Route path="identity/links" element={<AdminCortexIdentityLinksDrillPage />} />
                <Route path="identity/link-candidates" element={<AdminCortexIdentityLinkCandidatesDrillPage />} />
                <Route path="identity/merge-queue" element={<AdminCortexIdentityMergeQueueDrillPage />} />
                <Route path="identity/ambiguity-queue" element={<AdminCortexIdentityAmbiguityQueueDrillPage />} />
                <Route path="identity/replay-jobs" element={<AdminCortexIdentityReplayJobsDrillPage />} />
                <Route
                  path="identity/bundle-equivalence"
                  element={<AdminCortexIdentityBundleEquivalenceDrillPage />}
                />
                <Route path="identity/primitives" element={<AdminCortexIdentityPrimitivesDrillPage />} />
                <Route path="graph" element={<AdminCortexGraphPage />} />
                <Route path="traversal" element={<AdminCortexTraversalLayout />}>
                  <Route index element={<AdminCortexTraversalOverviewPage />} />
                  <Route path="control-plane" element={<AdminCortexTraversalControlPlanePage />} />
                </Route>
                <Route path="memory" element={<AdminCortexMemoryPage />} />
                <Route path="reasoning" element={<AdminCortexReasoningLayout />}>
                  <Route index element={<AdminCortexReasoningOverviewPage />} />
                  <Route path="jobs" element={<AdminCortexReasoningJobsPage />} />
                  <Route path="jobs/:jobId" element={<AdminCortexReasoningJobDetailPage />} />
                  <Route path="legality" element={<AdminCortexReasoningLegalityPage />} />
                  <Route
                    path="certification-pack"
                    element={<AdminCortexReasoningCertificationPackPage />}
                  />
                </Route>
                <Route path="retrieval" element={<AdminCortexRetrievalLayout />}>
                  <Route index element={<AdminCortexRetrievalOverviewPage />} />
                  <Route path="legality" element={<AdminCortexRetrievalLegalityPage />} />
                  <Route path="lineage" element={<AdminCortexRetrievalLineagePage />} />
                  <Route path="continuity" element={<AdminCortexRetrievalContinuityPage />} />
                </Route>
                <Route path="synthesis" element={<AdminCortexPlaceholderPage title="Synthesis" />} />
                <Route path="verification" element={<AdminCortexVerificationPage />} />
                <Route path="settings-debug" element={<AdminCortexPlaceholderPage title="Settings / Debug" />} />
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
