import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import PublicNav from "../components/PublicNav";
import { productApiBase, useProductMeQuery } from "../lib/meApi";
import { mergeProductSessionAuth, setStoredSessionToken } from "../lib/sessionToken";

async function logoutRequest(base: string): Promise<void> {
  const res = await fetch(`${base}/auth/logout`, mergeProductSessionAuth({ method: "POST" }));
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export default function RequireAuth() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const loc = useLocation();
  const navigate = useNavigate();
  const me = useProductMeQuery(apiBase);

  const lo = useMutation({
    mutationFn: () => logoutRequest(apiBase),
    onSuccess: async () => {
      setStoredSessionToken(null);
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      navigate("/", { replace: true });
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

  if (me.data.workspace_access_enabled === false) {
    return <Navigate to="/signup/waitlist" replace />;
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
