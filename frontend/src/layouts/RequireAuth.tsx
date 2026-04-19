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
      <div className="font-display relative flex h-[100dvh] max-h-[100dvh] min-h-0 flex-col overflow-hidden bg-[#FFFFFF] text-[#0F0F12] antialiased selection:bg-[#E878BE]/18 selection:text-[#0F0F12]">
        <div className="pointer-events-none fixed inset-0">
          <div className="absolute inset-0 bg-[#FFFFFF]" />
          <div
            className="absolute inset-0 opacity-[0.06]"
            style={{
              backgroundImage: `
              linear-gradient(to right, rgba(15, 15, 18, 0.05) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(15, 15, 18, 0.05) 1px, transparent 1px)
            `,
              backgroundSize: "56px 56px",
            }}
          />
        </div>
        <PublicNav />
        <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex flex-1 flex-col items-center justify-center gap-4 px-5 py-12">
            <div
              className="h-8 w-8 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
              aria-hidden
            />
            <p className="text-center text-base text-[#52525B]">Loading…</p>
          </div>
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
    <div className="font-display relative flex h-[100dvh] max-h-[100dvh] min-h-0 flex-col overflow-hidden bg-[#FFFFFF] text-[#0F0F12] antialiased selection:bg-[#E878BE]/18 selection:text-[#0F0F12]">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute inset-0 bg-[#FFFFFF]" />
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(15, 15, 18, 0.05) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(15, 15, 18, 0.05) 1px, transparent 1px)
            `,
            backgroundSize: "56px 56px",
          }}
        />
      </div>
      <PublicNav
        email={me.data.email}
        onLogout={() => lo.mutate()}
        showConnectors={showConnectorsNav}
      />
      {/*
        flex-1 min-h-0 lets child routes (e.g. onboarding) fill the viewport below the nav and
        scroll inside their own panel instead of growing the document.
      */}
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
