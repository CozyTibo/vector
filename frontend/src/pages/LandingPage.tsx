import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect } from "react";
import { useNavigate } from "react-router-dom";

import { VectorLandingBody } from "../components/landing/VectorLandingBody.tsx";
import MarketingLayout from "../components/marketing/MarketingLayout.tsx";
import { fetchMe, productApiBase, signedInDestination, useProductMeQuery } from "../lib/meApi.ts";
import { consumeSessionTokenFromOAuthRedirect, mergeProductSessionAuth, setStoredSessionToken } from "../lib/sessionToken.ts";

const LANDING_SCROLL_KEY = "vector:landing-scroll-y";

const WORKSPACE_ENTRY_LABEL = "Go to your workspace";

async function logoutRequest(base: string): Promise<void> {
  const res = await fetch(`${base}/auth/logout`, mergeProductSessionAuth({ method: "POST" }));
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export default function LandingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const apiBase = productApiBase();

  const me = useProductMeQuery(apiBase, {
    staleTime: 5 * 60_000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const lo = useMutation({
    mutationFn: () => logoutRequest(apiBase),
    onSuccess: async () => {
      setStoredSessionToken(null);
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    },
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_ok") !== "1") {
      return;
    }
    void (async () => {
      consumeSessionTokenFromOAuthRedirect();
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      const fresh = await fetchMe(apiBase);
      window.history.replaceState({}, "", window.location.pathname);
      navigate(fresh ? "/" : "/login", { replace: true });
    })();
  }, [apiBase, navigate, qc]);

  const landingReady = !me.isPending;

  useEffect(() => {
    if (!landingReady) return;
    const prev = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => {
      window.history.scrollRestoration = prev;
    };
  }, [landingReady]);

  useLayoutEffect(() => {
    if (!landingReady) return;
    const raw = sessionStorage.getItem(LANDING_SCROLL_KEY);
    if (raw == null) return;
    const y = Number.parseInt(raw, 10);
    if (Number.isNaN(y) || y < 0) return;
    requestAnimationFrame(() => {
      window.scrollTo(0, y);
    });
  }, [landingReady]);

  useEffect(() => {
    if (!landingReady) return;
    let idle: ReturnType<typeof setTimeout>;
    const save = () => {
      clearTimeout(idle);
      idle = setTimeout(() => {
        sessionStorage.setItem(LANDING_SCROLL_KEY, String(window.scrollY));
      }, 120);
    };
    window.addEventListener("scroll", save, { passive: true });
    const onHide = () => {
      if (document.visibilityState === "hidden") save();
    };
    document.addEventListener("visibilitychange", onHide);
    save();
    return () => {
      clearTimeout(idle);
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("scroll", save);
      sessionStorage.setItem(LANDING_SCROLL_KEY, String(window.scrollY));
    };
  }, [landingReady]);

  if (me.isPending) {
    return (
      <MarketingLayout bareBackground accentJoinListCta>
        <main className="flex min-h-[60vh] flex-col items-center justify-center px-6">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-pink-100 border-t-[#E878BE]" />
          <p className="mt-4 text-sm text-zinc-500">Loading…</p>
        </main>
      </MarketingLayout>
    );
  }

  const workspaceCta = me.data
    ? { to: signedInDestination(me.data), label: WORKSPACE_ENTRY_LABEL }
    : undefined;

  const signedSession = me.data
    ? {
        email: me.data.email,
        onSignOut: () => lo.mutate(),
        signOutPending: lo.isPending,
      }
    : undefined;

  return (
    <MarketingLayout
      bareBackground
      accentJoinListCta
      hideHeaderEmail
      signedSession={signedSession}
      workspaceNavCta={workspaceCta}
    >
      <VectorLandingBody signedInWorkspaceCta={workspaceCta} />
    </MarketingLayout>
  );
}
