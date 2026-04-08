import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AdminLayout from "./admin/AdminLayout.tsx";
import AdminDataPipelinePage from "./admin/AdminDataPipelinePage.tsx";
import AdminExecutionGraphPage from "./admin/AdminExecutionGraphPage.tsx";
import AdminIntegrationsPage from "./admin/AdminIntegrationsPage.tsx";
import AdminTenantOnboardingPage from "./admin/AdminTenantOnboardingPage.tsx";
import AdminTenantDebugPage from "./admin/AdminTenantDebugPage.tsx";
import AdminTenantHubPage from "./admin/AdminTenantHubPage.tsx";
import AdminTenantLayout from "./admin/AdminTenantLayout.tsx";
import AdminTenantDataSectionLayout from "./admin/AdminTenantDataSectionLayout.tsx";
import AdminTenantManagerOnboarding from "./admin/AdminTenantManagerOnboarding.tsx";
import AdminTenantStep3 from "./admin/AdminTenantStep3.tsx";
import AdminWorkspacePage from "./admin/AdminWorkspacePage.tsx";
import AdminWorkspacesPage from "./admin/AdminWorkspacesPage.tsx";
import {
  LegacyExecutionGraphRedirect,
  LegacyTenantDebugRedirect,
  RedirectManagerOnboardingSessionToTenant,
  RedirectStep1ToDataPipeline,
  RedirectStep2ToDataPipeline,
  RedirectStep3Actor,
  RedirectStep3Artifact,
  RedirectTenantToIntegrations,
  RedirectTenantToSlackOnboarding,
  RedirectTenantToWorkspace,
} from "./admin/adminRedirects.tsx";
import RequireAuth from "./layouts/RequireAuth.tsx";
import { sessionCanonicalClient } from "./lib/canonicalApi.ts";
import ActorDetailPage from "./pages/debug/ActorDetailPage.tsx";
import ArtifactDetailPage from "./pages/debug/ArtifactDetailPage.tsx";
import CanonicalDebugPage from "./pages/debug/CanonicalDebugPage.tsx";
import AppHomePage from "./pages/app/AppHomePage.tsx";
import ConnectorsPage from "./pages/app/ConnectorsPage.tsx";
import OnboardingPage from "./pages/app/OnboardingPage.tsx";
import LandingPage from "./pages/LandingPage.tsx";
import LoginPage from "./pages/LoginPage.tsx";
import ProjectionDebugPage from "./pages/ProjectionDebugPage.tsx";
import RawIngestionDebugPage from "./pages/RawIngestionDebugPage.tsx";
import SignupPage from "./pages/SignupPage.tsx";
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
          <Route path="/signup" element={<SignupPage />} />

          <Route element={<RequireAuth />}>
            <Route path="/app" element={<AppHomePage />} />
            <Route path="/app/onboarding" element={<OnboardingPage />} />
            <Route path="/app/connectors" element={<ConnectorsPage />} />
            <Route path="/app/github/ingestion" element={<Navigate to="/app/connectors" replace />} />
          </Route>

          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminWorkspacesPage />} />
            <Route path="workspaces" element={<Navigate to="/admin" replace />} />
            <Route path="manager-onboarding" element={<Navigate to="/admin" replace />} />
            <Route path="slack-onboarding" element={<Navigate to="/admin" replace />} />
            <Route
              path="manager-onboarding/sessions/:sessionId"
              element={<RedirectManagerOnboardingSessionToTenant />}
            />
            <Route
              path="execution-graph"
              element={
                <AdminTenantHubPage
                  title="Execution graph"
                  subtitle="Choose a workspace to explore people, work objects, relationships, and pipeline status after canonical processing."
                  pathSuffix="data-pipeline/execution-graph"
                />
              }
            />
            <Route
              path="pipelines"
              element={
                <AdminTenantHubPage
                  title="Pipelines"
                  subtitle="Choose a workspace to run connector syncs, inspect raw and projection rows, and open advanced resets."
                  pathSuffix="data-pipeline"
                />
              }
            />
            <Route
              path="debug"
              element={
                <AdminTenantHubPage
                  title="Debug"
                  subtitle="Choose a workspace for full raw, projection, and canonical table inspection."
                  pathSuffix="debug"
                />
              }
            />
            <Route path="tenants/:tenantId" element={<AdminTenantLayout />}>
              <Route index element={<Navigate to="workspace" replace />} />
              <Route path="workspace" element={<AdminWorkspacePage />} />
              <Route path="onboarding" element={<AdminTenantOnboardingPage />} />
              <Route path="overview" element={<RedirectTenantToWorkspace />} />
              <Route path="integrations" element={<AdminIntegrationsPage />} />
              <Route path="connections" element={<RedirectTenantToIntegrations />} />
              <Route path="slack-onboarding" element={<AdminTenantManagerOnboarding />} />
              <Route path="manager-onboarding" element={<RedirectTenantToSlackOnboarding />} />
              <Route path="data-pipeline" element={<AdminTenantDataSectionLayout />}>
                <Route index element={<AdminDataPipelinePage />} />
                <Route path="execution-graph">
                  <Route path="artifacts/:artifactId" element={<ArtifactDetailPage />} />
                  <Route path="actors/:actorId" element={<ActorDetailPage />} />
                  <Route index element={<AdminExecutionGraphPage />} />
                </Route>
                <Route path="debug" element={<AdminTenantDebugPage />} />
              </Route>
              <Route path="execution-graph/*" element={<LegacyExecutionGraphRedirect />} />
              <Route path="debug" element={<LegacyTenantDebugRedirect />} />
              <Route path="step1" element={<RedirectStep1ToDataPipeline />} />
              <Route path="step2" element={<RedirectStep2ToDataPipeline />} />
              <Route path="step3/artifacts/:artifactId" element={<RedirectStep3Artifact />} />
              <Route path="step3/actors/:actorId" element={<RedirectStep3Actor />} />
              <Route path="step3" element={<AdminTenantStep3 />} />
            </Route>
          </Route>

          <Route
            path="/debug/canonical"
            element={
              <CanonicalDebugPage
                client={sessionCanonicalClient()}
                entityBasePath="/debug/canonical"
                dashboardHref="/app"
              />
            }
          />
          <Route path="/debug/canonical/artifacts/:artifactId" element={<ArtifactDetailPage />} />
          <Route path="/debug/canonical/actors/:actorId" element={<ActorDetailPage />} />
          <Route
            path="/debug/connectors/:connector/:connectionId/projections"
            element={<ProjectionDebugPage />}
          />
          <Route path="/debug/ingestion/raw/:recordId" element={<RawIngestionDebugPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
