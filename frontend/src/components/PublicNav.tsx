import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import vectorHeroAvatarUrl from "../assets/logo.jpeg";
import { workspaceAppShellMaxWidth } from "./marketing/marketingStyles";
import { workspaceAuthGateLink, workspaceNavLinkCurrent, workspaceNavLinkRest } from "./workspace/workspaceUiTokens";

type Props = {
  email?: string;
  onLogout?: () => void;
  /** When false, hide workspace nav links (Signals, Access), e.g. during onboarding. */
  showConnectors?: boolean;
};

/**
 * 8-tooth gear — paths from Heroicons `Cog8ToothIcon` outline (MIT), matches standard settings/account affordance.
 */
function AccountGearIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        stroke="currentColor"
        d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 0 1 1.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.559.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.894.149c-.424.07-.764.383-.929.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 0 1-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.398.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 0 1-.12-1.45l.527-.737c.25-.35.272-.806.108-1.204-.165-.397-.506-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.108-1.204l-.526-.738a1.125 1.125 0 0 1 .12-1.45l.773-.773a1.125 1.125 0 0 1 1.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894Z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        stroke="currentColor"
        d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
      />
    </svg>
  );
}

function AccountMenu({ onLogout }: { onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) {
      return;
    }
    const onDocPointer = (e: MouseEvent | TouchEvent) => {
      const el = rootRef.current;
      if (!el?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocPointer);
    document.addEventListener("touchstart", onDocPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocPointer);
      document.removeEventListener("touchstart", onDocPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="flex h-10 w-10 items-center justify-center rounded-lg text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-400"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={open ? menuId : undefined}
        aria-label="Account and settings"
        onClick={() => setOpen((v) => !v)}
      >
        <AccountGearIcon className="shrink-0" />
      </button>
      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-label="Account"
          className="absolute right-0 top-full z-50 mt-2 min-w-[14rem] overflow-hidden rounded-xl border border-zinc-200/90 bg-white py-2 shadow-[0_16px_48px_-12px_rgba(15,23,42,0.22)] ring-1 ring-zinc-950/[0.06]"
        >
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center px-4 py-3 text-left text-base font-medium leading-normal text-zinc-800 transition-colors hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-none"
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default function PublicNav({ email, onLogout, showConnectors = false }: Props) {
  const loc = useLocation();
  const onSignals = loc.pathname === "/app";
  const onAccess = loc.pathname === "/app/access" || loc.pathname.startsWith("/app/access/");

  return (
    <header className="relative z-40 border-b border-zinc-200/90 bg-[#FFFFFF]/95 backdrop-blur-md">
      <div className={`mx-auto flex ${workspaceAppShellMaxWidth} items-center justify-between gap-4 px-5 py-4 sm:px-8 sm:py-5`}>
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
            <>
              <Link to="/app" className={onSignals ? workspaceNavLinkCurrent : workspaceNavLinkRest}>
                Signals
              </Link>
              <Link to="/app/access" className={onAccess ? workspaceNavLinkCurrent : workspaceNavLinkRest}>
                Access
              </Link>
            </>
          ) : null}
          {email ? (
            onLogout ? (
              <AccountMenu onLogout={onLogout} />
            ) : null
          ) : (
            <Link to="/login" className={workspaceAuthGateLink}>
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
