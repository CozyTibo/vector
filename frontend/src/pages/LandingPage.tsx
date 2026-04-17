import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect } from "react";
import { useNavigate } from "react-router-dom";

import { VectorLandingBody } from "../components/landing/VectorLandingBody.tsx";
import MarketingLayout from "../components/marketing/MarketingLayout.tsx";
import { fetchMe, productApiBase } from "../lib/meApi.ts";
import { consumeSessionTokenFromOAuthRedirect } from "../lib/sessionToken.ts";

const LANDING_SCROLL_KEY = "vector:landing-scroll-y";

export default function LandingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const apiBase = productApiBase();

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

  useEffect(() => {
    const prev = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => {
      window.history.scrollRestoration = prev;
    };
  }, []);

  useLayoutEffect(() => {
    const raw = sessionStorage.getItem(LANDING_SCROLL_KEY);
    if (raw == null) return;
    const y = Number.parseInt(raw, 10);
    if (Number.isNaN(y) || y < 0) return;
    requestAnimationFrame(() => {
      window.scrollTo(0, y);
    });
  }, []);

  useEffect(() => {
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
  }, []);

  return (
    <MarketingLayout bareBackground accentJoinListCta hideHeaderEmail>
      <VectorLandingBody />
    </MarketingLayout>
  );
}
