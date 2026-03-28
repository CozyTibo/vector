import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import MarketingLayout from "../components/marketing/MarketingLayout";
import { fetchMe, productApiBase } from "../lib/meApi";

function signedInDestination(me: NonNullable<Awaited<ReturnType<typeof fetchMe>>>): string {
  const mustFinishOnboarding =
    "onboarding_completed" in me && me.onboarding_completed !== true;
  return mustFinishOnboarding ? "/app/onboarding" : "/app";
}

function HeroSignalStack() {
  return (
    <div className="relative mx-auto h-[min(600px,80vh)] w-full max-w-[480px] lg:mx-0 lg:max-w-none">
      <div
        className="absolute left-[4%] top-[5%] z-[3] w-[88%] rotate-[-2deg] rounded-2xl border border-zinc-200/80 bg-white/75 p-4 shadow-[0_12px_48px_-20px_rgba(15,23,42,0.09),inset_0_0_0_1px_rgba(139,92,246,0.07)] backdrop-blur-xl sm:p-5"
        style={{ animation: "marketing-float-a 7s ease-in-out infinite" }}
      >
        <div className="flex items-center justify-between gap-3 border-b border-zinc-200/70 pb-3">
          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-600">Live signals</span>
          <span className="flex items-center gap-1.5 text-[10px] font-medium text-emerald-600">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Ingesting
          </span>
        </div>
        <div className="mt-4 space-y-3">
          <div className="flex items-start gap-3 rounded-xl bg-gradient-to-br from-violet-500/14 to-transparent p-3 ring-1 ring-violet-300/35">
            <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-violet-600 shadow-[0_0_10px_rgba(124,58,237,0.55)]" />
            <div>
              <p className="text-sm font-medium text-zinc-900">Execution stalled · Issue in progress but no commits in 12h</p>
              <p className="mt-0.5 text-xs text-zinc-500">GitHub ↔ Linear</p>
            </div>
          </div>
          <div className="h-px w-full bg-gradient-to-r from-transparent via-zinc-200 to-transparent" />
          <div className="flex items-start gap-3 rounded-xl bg-zinc-50/90 p-3 ring-1 ring-zinc-200/80">
            <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.55)]" />
            <div>
              <p className="text-sm font-medium text-zinc-800">Untracked work: discussion and PR open but no issue</p>
              <p className="mt-0.5 text-xs text-zinc-500">Linear ↔ GitHub ↔ Slack</p>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-xl bg-zinc-50/90 p-3 ring-1 ring-zinc-200/80">
            <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.45)]" />
            <div>
              <p className="text-sm font-medium text-zinc-800">Priority conflict detected: Checkout blocked by Payments team</p>
              <p className="mt-0.5 text-xs text-zinc-500">Linear ↔ GitHub · delay ~1d</p>
            </div>
          </div>
        </div>
      </div>

      <div
        className="absolute right-[2%] top-[56%] z-[2] w-[72%] rotate-[3deg] rounded-xl border border-violet-200/50 bg-white/85 p-3 shadow-[0_14px_40px_-18px_rgba(124,58,237,0.14),0_14px_40px_-18px_rgba(20,184,166,0.12)] backdrop-blur-md sm:p-4"
        style={{ animation: "marketing-float-b 8s ease-in-out infinite" }}
      >
        <p className="text-[10px] font-semibold uppercase tracking-widest text-violet-700">Execution graph</p>
        <div className="mt-3 flex h-14 items-end gap-1 sm:h-16">
          {[40, 72, 48, 88, 55, 95, 62].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t-sm bg-gradient-to-t from-violet-600/85 to-teal-400/90 opacity-95"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>

      <div
        className="absolute bottom-[4%] left-[12%] z-[1] w-[64%] rotate-[-4deg] rounded-xl border border-teal-200/55 bg-white/88 px-4 py-3 shadow-[0_12px_40px_-16px_rgba(124,58,237,0.1),0_12px_40px_-16px_rgba(20,184,166,0.12)] backdrop-blur-lg"
        style={{ animation: "marketing-float-c 9s ease-in-out infinite" }}
      >
        <p className="text-[11px] font-medium text-zinc-700">
          <span className="text-violet-600">→</span> Workflow depth <span className="text-zinc-400">· realtime</span>
        </p>
      </div>

      <style>{`
        @keyframes marketing-float-a {
          0%, 100% { transform: translateY(0) rotate(-2deg); }
          50% { transform: translateY(-10px) rotate(-1.5deg); }
        }
        @keyframes marketing-float-b {
          0%, 100% { transform: translateY(0) rotate(3deg); }
          50% { transform: translateY(8px) rotate(3.5deg); }
        }
        @keyframes marketing-float-c {
          0%, 100% { transform: translateY(0) rotate(-4deg); }
          50% { transform: translateY(-6px) rotate(-3deg); }
        }
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
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_ok") === "1") {
      void qc.invalidateQueries({ queryKey: ["me", apiBase] });
      window.history.replaceState({}, "", window.location.pathname);
      navigate("/app", { replace: true });
    }
  }, [apiBase, navigate, qc]);

  if (me.isPending) {
    return (
      <MarketingLayout>
        <main className="flex min-h-[60vh] flex-col items-center justify-center px-6">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
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
      <main className="mx-auto max-w-6xl px-5 pb-20 pt-6 sm:px-8 sm:pb-28 sm:pt-4 lg:pt-2">
        <div className="grid items-center gap-12 lg:grid-cols-12 lg:gap-8 lg:pt-4">
          <div className="relative z-[1] lg:col-span-6 lg:pl-2">
            <p className="mb-5 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-violet-700">
              <span className="h-px w-8 bg-gradient-to-r from-violet-600 via-teal-500 to-transparent" />
              Early access
            </p>

            <h1 className="max-w-xl text-[2.65rem] font-bold leading-[0.96] tracking-tight text-zinc-900 sm:text-6xl lg:text-[3.5rem] lg:leading-[0.95]">
              Make execution observable.
              <br />
              <span className="bg-gradient-to-r from-violet-600 via-purple-600 to-teal-500 bg-clip-text text-transparent">
               
               Make it predictable.
              </span>
            </h1>
            <p className="mt-6 max-w-md text-base leading-relaxed text-zinc-600 sm:text-lg">
              Vector analyzes signals across your tools to reconstruct how execution actually happens.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3 sm:mt-10">
              <Link
                to="/signup"
                className="inline-flex items-center justify-center rounded-full bg-zinc-900 px-7 py-3.5 text-sm font-semibold text-white no-underline shadow-[0_6px_32px_-8px_rgba(20,184,166,0.38),0_2px_12px_-6px_rgba(124,58,237,0.18)] transition-[transform,box-shadow] hover:scale-[1.02] hover:shadow-[0_8px_36px_-6px_rgba(6,182,212,0.28),0_2px_14px_-4px_rgba(139,92,246,0.22)]"
              >
                Get started
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-full border border-zinc-200/90 bg-white/75 px-7 py-3.5 text-sm font-semibold text-zinc-800 no-underline shadow-[0_2px_16px_-8px_rgba(15,23,42,0.06)] backdrop-blur-sm transition-colors hover:border-zinc-300 hover:bg-white"
              >
                Sign in
              </Link>
            </div>
          </div>

          <div className="relative z-0 lg:col-span-6 lg:-mr-4">
            <HeroSignalStack />
          </div>
        </div>
      </main>
    </MarketingLayout>
  );
}
