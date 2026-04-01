import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import PublicNav from "../components/PublicNav";
import { fetchMe, productApiBase } from "../lib/meApi";

async function logoutRequest(base: string): Promise<void> {
  const res = await fetch(`${base}/auth/logout`, { method: "POST", credentials: "include" });
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export default function RequireAuth() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const loc = useLocation();
  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });

  const lo = useMutation({
    mutationFn: () => logoutRequest(apiBase),
    onSuccess: () => {
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      void qc.invalidateQueries({ queryKey: ["me", apiBase] });
    },
  });

  if (me.isPending) {
    return (
      <div className="flex h-[100dvh] max-h-[100dvh] min-h-0 flex-col overflow-hidden bg-stone-50">
        <PublicNav />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <p className="p-8 text-stone-600">Loading…</p>
        </div>
      </div>
    );
  }

  if (!me.data) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }

  const onOnboardingRoute = loc.pathname === "/app/onboarding" || loc.pathname.startsWith("/app/onboarding/");
  const mustFinishOnboarding =
    "onboarding_completed" in me.data && me.data.onboarding_completed !== true;
  if (mustFinishOnboarding && !onOnboardingRoute) {
    return <Navigate to="/app/onboarding" replace />;
  }

  const showConnectorsNav =
    !("onboarding_completed" in me.data) || me.data.onboarding_completed === true;

  return (
    <div className="flex h-[100dvh] max-h-[100dvh] min-h-0 flex-col overflow-hidden bg-stone-50">
      <PublicNav
        email={me.data.email}
        onLogout={() => lo.mutate()}
        showConnectors={showConnectorsNav}
      />
      {/*
        flex-1 min-h-0 lets child routes (e.g. onboarding) fill the viewport below the nav and
        scroll inside their own panel instead of growing the document.
      */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
