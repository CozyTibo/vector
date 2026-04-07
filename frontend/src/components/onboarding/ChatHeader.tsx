import type { ReactNode } from "react";

import vectorHeroAvatarUrl from "../../assets/vector-hero-avatar.png";
import { landingAccentText } from "../landing/landingBrandPalette";

type ChatHeaderProps = {
  /** e.g. “Start over” for a fresh onboarding run */
  trailing?: ReactNode;
};

/**
 * In-card header — teammate DM identity (matches landing hero Vector treatment).
 */
export default function ChatHeader({ trailing }: ChatHeaderProps) {
  return (
    <header className="shrink-0 border-b border-zinc-100/95 bg-white/90 px-4 py-3.5 sm:px-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="inline-flex h-11 w-11 shrink-0 overflow-hidden rounded-2xl bg-zinc-50 shadow-md ring-2 ring-[#F5C8E0]/90">
            <img
              src={vectorHeroAvatarUrl}
              alt=""
              className="h-full w-full object-cover object-center"
              width={44}
              height={44}
              decoding="async"
            />
          </span>
          <div className="min-w-0">
            <h2 className={`truncate text-base font-semibold tracking-tight ${landingAccentText}`}>Vector</h2>
            <p className="truncate text-[13px] font-medium text-zinc-500">Execution manager</p>
          </div>
        </div>
        {trailing ? <div className="shrink-0 self-start pt-0.5 sm:self-center sm:pt-0">{trailing}</div> : null}
      </div>
    </header>
  );
}
