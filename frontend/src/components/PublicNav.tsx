import { Link } from "react-router-dom";

import vectorHeroAvatarUrl from "../assets/vector-hero-avatar.png";
import { marketingAccentLink, marketingMutedLink } from "./marketing/marketingStyles";

type Props = {
  email?: string;
  onLogout?: () => void;
  /** When false, hide product nav to Connectors (e.g. during onboarding). */
  showConnectors?: boolean;
};

export default function PublicNav({ email, onLogout, showConnectors = false }: Props) {
  return (
    <header className="relative z-40 border-b border-zinc-200/90 bg-[#FFFFFF]/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-[96rem] items-center justify-between gap-4 px-5 py-4 sm:px-8 sm:py-5">
        <Link
          to="/app"
          className="group flex items-center gap-2.5 text-lg font-semibold tracking-[-0.02em] text-[#0F0F12] no-underline outline-none transition-opacity hover:opacity-90 sm:text-xl"
          aria-label="Vector home"
        >
          <img
            src={vectorHeroAvatarUrl}
            alt=""
            className="h-9 w-9 shrink-0 rounded-full border-2 border-white object-cover shadow-[0_1px_3px_rgba(0,0,0,0.08)] outline outline-1 outline-offset-0 outline-zinc-200/80 transition-transform duration-300 group-hover:scale-105 sm:h-10 sm:w-10"
            decoding="async"
          />
          Vector
        </Link>
        <nav className="flex min-w-0 max-w-[min(100%,36rem)] flex-wrap items-center justify-end gap-3 text-sm font-medium sm:gap-4">
          {showConnectors ? (
            <Link to="/app/connectors" className={`${marketingAccentLink} text-sm`}>
              Connectors
            </Link>
          ) : null}
          {email ? (
            <>
              <span className="max-w-[14rem] truncate text-[#52525B]" title={email}>
                {email}
              </span>
              {onLogout ? (
                <button
                  type="button"
                  className={`${marketingMutedLink} cursor-pointer border-0 bg-transparent p-0 underline decoration-zinc-300`}
                  onClick={onLogout}
                >
                  Sign out
                </button>
              ) : null}
            </>
          ) : (
            <Link to="/login" className={marketingAccentLink}>
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
