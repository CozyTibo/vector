/**
 * Marketing landing (hero + below-fold). Golden reference: `src/vector-landing-snapshot/`.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import vectorHeroAvatarUrl from "../assets/vector-hero-avatar.png";
import heroAlexAvatarUrl from "../assets/hero-org-michelle.png";
import {
  landingAccentRgb,
  landingAccentText,
  landingSubtleLineV,
  landingTitleKeywordGradient,
} from "../components/landing/landingBrandPalette";
import { LandingBelowHero } from "../components/landing/LandingBelowHero";
import MarketingLayout from "../components/marketing/MarketingLayout";
import { fetchMe, productApiBase } from "../lib/meApi";

const LANDING_SCROLL_KEY = "vector:landing-scroll-y";

const heroVectorBubbleAccentClass = `pointer-events-none absolute bottom-0 left-0 top-0 w-[3px] ${landingSubtleLineV}`;

function signedInDestination(me: NonNullable<Awaited<ReturnType<typeof fetchMe>>>): string {
  const mustFinishOnboarding =
    "onboarding_completed" in me && me.onboarding_completed !== true;
  return mustFinishOnboarding ? "/app/onboarding" : "/app";
}

function VectorHeroAvatar({ className }: { className: string }) {
  return (
    <img
      src={vectorHeroAvatarUrl}
      alt="Vector"
      width={128}
      height={128}
      className={className}
      decoding="async"
    />
  );
}

/** Same footprint as Alex’s avatar; pulse is box-shadow only (no layout growth). */
function VectorHeroAvatarPulseWrap({ dimmed }: { dimmed?: boolean }) {
  return (
    <VectorHeroAvatar
      className={`hero-vector-avatar-pulse h-9 w-9 shrink-0 rounded-2xl object-cover ring-2 ring-[#F5C8E0]/90 sm:h-10 sm:w-10 ${dimmed ? "opacity-90" : ""}`}
    />
  );
}

function HeroNotionGlyph({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3 2.5h7l3 3v8a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z"
        className="stroke-zinc-500"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
      <path d="M10 2.5V5h2.5" className="stroke-zinc-500" strokeWidth="1.1" strokeLinejoin="round" />
    </svg>
  );
}

function HeroChatThread() {
  const alexAvatarClass =
    "h-9 w-9 shrink-0 rounded-full object-cover object-center shadow-md ring-2 ring-white ring-offset-1 ring-offset-zinc-100/80 sm:h-10 sm:w-10";

  return (
    <div className="pointer-events-none w-full select-none pb-2">
      <div className="w-full rounded-2xl border border-zinc-200/80 bg-white p-5 shadow-[0_20px_50px_-28px_rgba(15,23,42,0.12)] sm:p-6 lg:p-7">
        <div className="mb-5 flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-zinc-100/95 pb-4">
          <span className="text-[12px] font-semibold tracking-tight text-zinc-800"># checkout</span>
          <span className="text-[11px] text-zinc-400">·</span>
          <span className="text-[11px] font-medium text-zinc-500">Engineering</span>
        </div>

        <div className="space-y-5 sm:space-y-5">
          {/* Alex */}
          <div className="flex gap-3 sm:gap-3.5">
            <img src={heroAlexAvatarUrl} alt="Alex" className={alexAvatarClass} width={40} height={40} decoding="async" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <span className="text-sm font-semibold text-zinc-900">Alex</span>
                  <span className="text-[11px] font-medium text-zinc-500">Engineering Manager</span>
                  <span className="inline-flex items-center gap-1 rounded-md border border-zinc-200/90 bg-white/90 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-zinc-600 shadow-sm">
                    <HeroNotionGlyph className="h-3 w-3 shrink-0" />
                    Notion
                  </span>
                </div>
                <time className="text-[10px] font-medium tabular-nums text-zinc-400" dateTime="09:41">
                  9:41 AM
                </time>
              </div>
              <div className="mt-1.5 rounded-2xl rounded-tl-md border border-zinc-200/70 bg-zinc-100/90 px-3.5 py-2.5 text-[13px] font-normal leading-relaxed text-zinc-800 sm:text-[14px]">
                <p>Hey! just read the checkout update in the Notion report you sent me.</p>
                <p className="mt-2">Did we figure out why it slipped?</p>
              </div>
            </div>
          </div>

          {/* Vector */}
          <div className="flex gap-3 sm:gap-3.5">
            <VectorHeroAvatarPulseWrap />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <span className={`text-sm font-semibold ${landingAccentText}`}>Vector</span>
                <time className="text-[10px] font-medium tabular-nums text-zinc-400" dateTime="09:42">
                  9:42 AM
                </time>
              </div>
              <div className="relative mt-1.5 overflow-hidden rounded-2xl rounded-tl-md border border-zinc-200/70 bg-zinc-50/90 pl-[13px] pr-3.5 py-2.5 text-[13px] font-normal leading-relaxed text-zinc-800 sm:text-[14px]">
                <div className={heroVectorBubbleAccentClass} aria-hidden />
                <p className="relative">Yeah, I dug into it earlier.</p>
                <p className="relative mt-2">
                  The checkout refactor depends on the new auth middleware. That PR has been waiting for review since
                  yesterday.
                </p>
              </div>
            </div>
          </div>

          {/* Alex */}
          <div className="flex gap-3 sm:gap-3.5">
            <img src={heroAlexAvatarUrl} alt="Alex" className={alexAvatarClass} width={40} height={40} decoding="async" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <div className="flex flex-wrap items-center gap-x-2">
                  <span className="text-sm font-semibold text-zinc-900">Alex</span>
                  <span className="text-[11px] font-medium text-zinc-500">Engineering Manager</span>
                </div>
                <time className="text-[10px] font-medium tabular-nums text-zinc-400" dateTime="09:43">
                  9:43 AM
                </time>
              </div>
              <div className="mt-1.5 rounded-2xl rounded-tl-md border border-zinc-200/70 bg-zinc-100/90 px-3.5 py-2.5 text-[13px] font-normal leading-relaxed text-zinc-800 sm:text-[14px]">
                <p>Ah got it. Is that blocking the launch?</p>
              </div>
            </div>
          </div>

          {/* Vector */}
          <div className="flex gap-3 sm:gap-3.5">
            <VectorHeroAvatarPulseWrap />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <span className={`text-sm font-semibold ${landingAccentText}`}>Vector</span>
                <time className="text-[10px] font-medium tabular-nums text-zinc-400" dateTime="09:43:30">
                  9:43 AM
                </time>
              </div>
              <div className="relative mt-1.5 overflow-hidden rounded-2xl rounded-tl-md border border-zinc-200/70 bg-zinc-50/90 pl-[13px] pr-3.5 py-2.5 text-[13px] font-normal leading-relaxed text-zinc-800 sm:text-[14px]">
                <div className={heroVectorBubbleAccentClass} aria-hidden />
                <p className="relative">Not fully yet, but it might slow things down if it stays open.</p>
                <p className="relative mt-2">
                  Might be worth pulling someone from platform to review it today.
                </p>
              </div>
            </div>
          </div>

          {/* Alex */}
          <div className="flex gap-3 sm:gap-3.5">
            <img src={heroAlexAvatarUrl} alt="Alex" className={alexAvatarClass} width={40} height={40} decoding="async" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <div className="flex flex-wrap items-center gap-x-2">
                  <span className="text-sm font-semibold text-zinc-900">Alex</span>
                  <span className="text-[11px] font-medium text-zinc-500">Engineering Manager</span>
                </div>
                <time className="text-[10px] font-medium tabular-nums text-zinc-400" dateTime="09:44">
                  9:44 AM
                </time>
              </div>
              <div className="mt-1.5 rounded-2xl rounded-tl-md border border-zinc-200/70 bg-zinc-100/90 px-3.5 py-2.5 text-[13px] font-normal leading-relaxed text-zinc-800 sm:text-[14px]">
                <p>Makes sense. Who should we ask?</p>
              </div>
            </div>
          </div>

          {/* Vector */}
          <div className="flex gap-3 sm:gap-3.5">
            <VectorHeroAvatarPulseWrap />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <span className={`text-sm font-semibold ${landingAccentText}`}>Vector</span>
                <time className="text-[10px] font-medium tabular-nums text-zinc-400" dateTime="09:44:30">
                  9:44 AM
                </time>
              </div>
              <div className="relative mt-1.5 overflow-hidden rounded-2xl rounded-tl-md border border-zinc-200/70 bg-zinc-50/90 pl-[13px] pr-3.5 py-2.5 text-[13px] font-normal leading-relaxed text-zinc-800 sm:text-[14px]">
                <div className={heroVectorBubbleAccentClass} aria-hidden />
                <p className="relative">I can ping Sam. He worked on the middleware last week and should have context.</p>
              </div>
            </div>
          </div>

          {/* Typing */}
          <div className="flex gap-3 sm:gap-3.5 pt-0.5">
            <VectorHeroAvatarPulseWrap dimmed />
            <div className="flex min-h-[2.25rem] items-center rounded-2xl rounded-tl-md border border-zinc-200/60 bg-zinc-100/70 px-3.5 py-2">
              <div className="flex items-center gap-1" aria-hidden>
                <span className="hero-chat-typing-dot inline-block h-1.5 w-1.5 rounded-full bg-zinc-400" />
                <span className="hero-chat-typing-dot inline-block h-1.5 w-1.5 rounded-full bg-zinc-400" />
                <span className="hero-chat-typing-dot inline-block h-1.5 w-1.5 rounded-full bg-zinc-400" />
              </div>
              <span className="sr-only">Vector is typing</span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes hero-vector-avatar-pulse {
          0%, 100% {
            box-shadow: 0 4px 14px -5px rgba(${landingAccentRgb}, 0.32);
          }
          50% {
            box-shadow:
              0 4px 14px -5px rgba(${landingAccentRgb}, 0.42),
              0 0 0 2px rgba(${landingAccentRgb}, 0.22),
              0 0 16px rgba(246, 200, 230, 0.45);
          }
        }
        .hero-vector-avatar-pulse {
          animation: hero-vector-avatar-pulse 2.75s ease-in-out infinite;
        }
        @keyframes hero-chat-typing-dot {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
          30% { transform: translateY(-3px); opacity: 1; }
        }
        .hero-chat-typing-dot {
          animation: hero-chat-typing-dot 1.05s ease-in-out infinite;
        }
        .hero-chat-typing-dot:nth-child(2) { animation-delay: 0.18s; }
        .hero-chat-typing-dot:nth-child(3) { animation-delay: 0.36s; }
      `}</style>
    </div>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const apiBase = productApiBase();

  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
    /** Session rarely changes on the marketing surface; keep cache warm so revisiting does not refetch like a full reload */
    staleTime: 5 * 60_000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_ok") === "1") {
      void qc.removeQueries({ queryKey: ["onboarding", apiBase] });
      void qc.removeQueries({ queryKey: ["connectors", apiBase] });
      void qc.invalidateQueries({ queryKey: ["me", apiBase] });
      window.history.replaceState({}, "", window.location.pathname);
      navigate("/app", { replace: true });
    }
  }, [apiBase, navigate, qc]);

  /** `isLoading` = no cached data yet (unlike `isPending`, which can stay true during background refetch) */
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
      <MarketingLayout>
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
    <MarketingLayout>
      <main>
        {/* Hero */}
        <div className="mx-auto max-w-[96rem] px-5 pb-20 pt-6 sm:px-8 sm:pb-28 sm:pt-4 lg:pt-2">
          <div className="grid items-center gap-12 lg:grid-cols-12 lg:gap-12 lg:pt-4">
            <div className="relative z-[1] min-w-0 lg:col-span-6 lg:pl-2 lg:pr-2">
              <p
                className={`mb-6 inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.25em] ${landingAccentText}`}
              >
                <span className="h-px w-10 bg-[#E878BE]" />
                Early access
              </p>

              <h1 className="max-w-none text-[clamp(1.35rem,4.35vw+0.85rem,4.1rem)] font-bold leading-[1.03] tracking-[-0.02em] text-[#0F0F12]">
                <span className="whitespace-nowrap">Stop chasing updates.</span>
                <br aria-hidden />
                <span className="whitespace-nowrap">
                  Start making{" "}
                  <span className={landingTitleKeywordGradient}>
                    decisions
                  </span>
                  .
                </span>
              </h1>
              <p className="mt-7 max-w-2xl text-pretty text-xl leading-snug text-zinc-600 sm:mt-8 sm:text-2xl sm:leading-snug">
                <span className={`font-semibold ${landingAccentText}`}>Vector</span> joins your team as an{" "}
                <span className="font-semibold text-[#0F0F12]">execution manager</span>, keeping track of progress
                and <span className="font-semibold text-[#0F0F12]">tackling bottlenecks</span>.
              </p>
              <div className="mt-9 flex flex-wrap items-center gap-4 sm:mt-11">
                <Link
                  to="/signup"
                  className="inline-flex items-center justify-center rounded-full bg-[#0F0F12] px-9 py-4 text-base font-semibold text-white no-underline shadow-[0_8px_28px_-12px_rgba(15,23,42,0.35)] transition-[transform,box-shadow] hover:scale-[1.02] hover:shadow-[0_12px_36px_-12px_rgba(15,23,42,0.22)]"
                >
                  Get early access
                </Link>
                <a
                  href="#meet-vector-agent"
                  className="inline-flex items-center justify-center rounded-full border border-zinc-200/90 bg-[#FFFFFF]/75 px-9 py-4 text-base font-semibold text-[#0F0F12] no-underline shadow-[0_2px_16px_-8px_rgba(15,15,18,0.06)] backdrop-blur-sm transition-colors hover:border-zinc-300 hover:bg-white"
                >
                  See how it works
                </a>
              </div>
            </div>

            <div className="relative z-0 min-w-0 lg:col-span-6 lg:-mr-2 lg:pl-1">
              <HeroChatThread />
            </div>
          </div>
        </div>

        <LandingBelowHero />
      </main>
    </MarketingLayout>
  );
}
