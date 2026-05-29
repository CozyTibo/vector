import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AdminLayout from "./admin/AdminLayout.tsx";
import AdminCortexCanonEntityPage from "./admin/AdminCortexCanonEntityPage.tsx";
import AdminCortexCanonPage from "./admin/AdminCortexCanonPage.tsx";
import AdminCortexIdentitiesPage from "./admin/AdminCortexIdentitiesPage.tsx";
import AdminCortexGraphPage from "./admin/AdminCortexGraphPage.tsx";
import AdminCortexDeclaredDomainsPage from "./admin/AdminCortexDeclaredDomainsPage.tsx";
import AdminCortexIngestionPage from "./admin/AdminCortexIngestionPage.tsx";
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
                <Route index element={<Navigate to="ingestion" replace />} />
                <Route path="ingestion" element={<AdminCortexIngestionPage />} />
                <Route path="canon" element={<AdminCortexCanonPage />} />
                <Route path="canon/entities/:entityId" element={<AdminCortexCanonEntityPage />} />
                <Route path="identities" element={<AdminCortexIdentitiesPage />} />
                <Route path="links" element={<AdminCortexGraphPage />} />
                <Route path="declared-domains" element={<AdminCortexDeclaredDomainsPage />} />
                <Route path="overview" element={<Navigate to="ingestion" replace />} />
                <Route path="runtime" element={<Navigate to="ingestion" replace />} />
                <Route path="queues" element={<Navigate to="ingestion" replace />} />
                <Route path="people" element={<Navigate to="ingestion" replace />} />
                <Route path="people/:personId" element={<Navigate to="ingestion" replace />} />
                <Route path="canonical" element={<Navigate to="ingestion" replace />} />
                <Route path="canonical/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="inspect" element={<Navigate to="ingestion" replace />} />
                <Route path="inspect/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="settings" element={<Navigate to="ingestion" replace />} />
                <Route path="identity" element={<Navigate to="identities" replace />} />
                <Route path="identity/*" element={<Navigate to="../identities" replace />} />
                <Route path="graph" element={<Navigate to="links" replace />} />
                <Route path="reconstruction" element={<Navigate to="ingestion" replace />} />
                <Route path="reconstruction/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="retrieval" element={<Navigate to="ingestion" replace />} />
                <Route path="retrieval/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="synthesis" element={<Navigate to="ingestion" replace />} />
                <Route path="synthesis/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="entity-resolution" element={<Navigate to="ingestion" replace />} />
                <Route path="identity-certification" element={<Navigate to="ingestion" replace />} />
                <Route path="traversal" element={<Navigate to="ingestion" replace />} />
                <Route path="traversal/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="memory" element={<Navigate to="ingestion" replace />} />
                <Route path="reasoning" element={<Navigate to="ingestion" replace />} />
                <Route path="reasoning/*" element={<Navigate to="../ingestion" replace />} />
                <Route path="verification" element={<Navigate to="ingestion" replace />} />
                <Route path="settings-debug" element={<Navigate to="ingestion" replace />} />
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
