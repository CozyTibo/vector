import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { VectorLandingBody } from "../components/landing/VectorLandingBody.tsx";
import MarketingLayout from "../components/marketing/MarketingLayout.tsx";
import { fetchMe, productApiBase, signedInDestination } from "../lib/meApi.ts";

const LANDING_SCROLL_KEY = "vector:landing-scroll-y";

export default function LandingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const apiBase = productApiBase();

  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
    staleTime: 5 * 60_000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_ok") !== "1") {
      return;
    }
    void (async () => {
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      const fresh = await fetchMe(apiBase);
      window.history.replaceState({}, "", window.location.pathname);
      navigate(fresh ? signedInDestination(fresh) : "/login", { replace: true });
    })();
  }, [apiBase, navigate, qc]);

  const showLanding = !me.isLoading && !me.data;

  useEffect(() => {
    if (!showLanding) return;
    const prev = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => {
      window.history.scrollRestoration = prev;
    };
  }, [showLanding]);

  useLayoutEffect(() => {
    if (!showLanding) return;
    const raw = sessionStorage.getItem(LANDING_SCROLL_KEY);
    if (raw == null) return;
    const y = Number.parseInt(raw, 10);
    if (Number.isNaN(y) || y < 0) return;
    requestAnimationFrame(() => {
      window.scrollTo(0, y);
    });
  }, [showLanding]);

  useEffect(() => {
    if (!showLanding) return;
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
  }, [showLanding]);

  if (me.isLoading) {
    return (
      <MarketingLayout bareBackground accentJoinListCta>
        <main className="flex min-h-[60vh] flex-col items-center justify-center px-6">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-pink-100 border-t-[#E878BE]" />
          <p className="mt-4 text-sm text-zinc-500">Loading…</p>
        </main>
      </MarketingLayout>
    );
  }

  if (me.data) {
    return <Navigate to={signedInDestination(me.data)} replace />;
  }

  return (
    <MarketingLayout bareBackground accentJoinListCta>
      <VectorLandingBody />
    </MarketingLayout>
  );
}
