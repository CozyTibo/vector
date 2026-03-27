import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AdminLayout from "./admin/AdminLayout.tsx";
import AdminTenantConnections from "./admin/AdminTenantConnections.tsx";
import AdminTenantLayout from "./admin/AdminTenantLayout.tsx";
import AdminTenantOverview from "./admin/AdminTenantOverview.tsx";
import AdminTenantsPage from "./admin/AdminTenantsPage.tsx";
import AdminTenantStep1 from "./admin/AdminTenantStep1.tsx";
import AdminTenantStep2 from "./admin/AdminTenantStep2.tsx";
import AdminTenantStep3 from "./admin/AdminTenantStep3.tsx";
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
            <Route index element={<AdminTenantsPage />} />
            <Route path="tenants/:tenantId" element={<AdminTenantLayout />}>
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<AdminTenantOverview />} />
              <Route path="connections" element={<AdminTenantConnections />} />
              <Route path="step1" element={<AdminTenantStep1 />} />
              <Route path="step2" element={<AdminTenantStep2 />} />
              <Route path="step3" element={<AdminTenantStep3 />} />
              <Route path="step3/artifacts/:artifactId" element={<ArtifactDetailPage />} />
              <Route path="step3/actors/:actorId" element={<ActorDetailPage />} />
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
