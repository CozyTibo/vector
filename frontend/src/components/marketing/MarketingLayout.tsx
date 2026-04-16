import { Link } from "react-router-dom";

import vectorHeroAvatarUrl from "../../assets/vector-hero-avatar.png";
import vectorLogoUrl from "../../assets/vector-logo.png";

/** Signed-in marketing pages: logo + session actions (no Sign in / Join the list). */
export type MarketingLayoutSignedSession =
  | { email: string; onSignOut: () => void; signOutPending?: boolean }
  /** Session expected but details not loaded yet (e.g. /me pending). */
  | "pending";

type Props = {
  children: React.ReactNode;
  /** When false, only background + font (e.g. nested use). Default shows top chrome. */
  showChrome?: boolean;
  /** When true, skip the fixed marketing grid (e.g. home uses vector-landing’s own backdrop). */
  bareBackground?: boolean;
  /** Landing only: pink “Join the list” header CTA to match in-page CTAs. */
  accentJoinListCta?: boolean;
  /**
   * When set, replaces marketing nav with session UI (email + Sign out).
   * Omit for default Sign in + Join the list.
   */
  signedSession?: MarketingLayoutSignedSession;
};

const joinListNavCta =
  "rounded-full bg-[#E878BE] px-4 py-2 text-sm font-semibold text-white no-underline shadow-[0_6px_20px_-8px_rgba(232,120,190,0.45)] transition-[transform,box-shadow] hover:scale-[1.02] hover:bg-[#df6aad] hover:text-white hover:shadow-[0_8px_28px_-8px_rgba(232,120,190,0.4)] sm:px-5";

export default function MarketingLayout({
  children,
  showChrome = true,
  bareBackground = false,
  accentJoinListCta = false,
  signedSession,
}: Props) {
  return (
    <div className="font-display relative min-h-screen overflow-x-hidden bg-[#FFFFFF] text-[#0F0F12] antialiased selection:bg-[#E878BE]/18 selection:text-[#0F0F12]">
      {!bareBackground ? (
        <div className="pointer-events-none fixed inset-0">
          <div className="absolute inset-0 bg-[#FFFFFF]" />
          {/* Match `#vector-landing .page-bg__grid` (56px, subtle) */}
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
      ) : null}

      {showChrome ? (
        <header className="relative z-20 mx-auto flex max-w-[96rem] items-center justify-between gap-4 px-5 pt-7 pb-4 sm:px-8 sm:pt-8">
          <Link
            to="/"
            className="group flex items-center gap-2.5 no-underline outline-none transition-opacity hover:opacity-90"
            aria-label="Vector home"
          >
            {accentJoinListCta ? (
              <>
                <img
                  src={vectorHeroAvatarUrl}
                  alt=""
                  className="h-9 w-9 shrink-0 rounded-full border-2 border-white object-cover shadow-[0_1px_3px_rgba(0,0,0,0.08)] outline outline-1 outline-offset-0 outline-zinc-200/80 transition-transform duration-300 group-hover:scale-105 sm:h-10 sm:w-10"
                  decoding="async"
                />
                <span className="text-lg font-semibold tracking-[-0.02em] text-[#0F0F12] sm:text-xl">Vector</span>
              </>
            ) : (
              <>
                <img
                  src={vectorLogoUrl}
                  alt=""
                  className="h-9 w-auto shrink-0 transition-transform duration-300 group-hover:scale-105 sm:h-10"
                  decoding="async"
                />
                <span className="text-lg font-semibold tracking-[-0.02em] text-[#0F0F12] sm:text-xl">Vector</span>
              </>
            )}
          </Link>
          {signedSession ? (
            <nav className="flex min-w-0 max-w-[min(100%,28rem)] items-center justify-end gap-3 sm:gap-4">
              {signedSession === "pending" ? (
                <span className="text-sm text-[#52525B]">Loading…</span>
              ) : (
                <>
                  <span
                    className="min-w-0 max-w-[11rem] truncate text-sm text-[#52525B] sm:max-w-[18rem]"
                    title={signedSession.email}
                  >
                    {signedSession.email}
                  </span>
                  <button
                    type="button"
                    disabled={Boolean(signedSession.signOutPending)}
                    className="shrink-0 rounded-full border border-zinc-200/90 bg-white/90 px-4 py-2 text-sm font-semibold text-[#27272a] transition-[border-color,background-color] hover:border-zinc-300 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={() => signedSession.onSignOut()}
                  >
                    {signedSession.signOutPending ? "Signing out…" : "Sign out"}
                  </button>
                </>
              )}
            </nav>
          ) : (
            <nav className="flex items-center gap-2 sm:gap-3">
              <Link
                to="/login"
                className="rounded-full px-4 py-2 text-sm font-semibold text-[#52525B] no-underline transition-colors hover:text-[#0F0F12]"
              >
                Sign in
              </Link>
              <Link to="/signup" className={joinListNavCta}>
                Join the list
              </Link>
            </nav>
          )}
        </header>
      ) : null}

      <div className="relative z-10">{children}</div>
    </div>
  );
}
