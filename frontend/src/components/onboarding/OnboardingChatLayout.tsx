import type { ReactNode } from "react";

import ChatHeader from "./ChatHeader";

/** Same subtle grid as `MarketingLayout` — aligns onboarding with the landing world. */
const gridBgStyle = {
  backgroundImage: `
    linear-gradient(rgba(15,15,18,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15,15,18,0.05) 1px, transparent 1px)
  `,
  backgroundSize: "72px 72px",
} as const;

type OnboardingChatLayoutProps = {
  children: ReactNode;
  /** Bottom slot (input bar, tool selector, or connector actions) */
  footer?: ReactNode;
  /** Hide in-card header (e.g. rare full-bleed variants) */
  showHeader?: boolean;
  /** Right side of the in-card header (only when ``showHeader`` is true) */
  headerTrailing?: ReactNode;
};

/**
 * Full-viewport shell: marketing grid + centered card (landing demo–like).
 */
export default function OnboardingChatLayout({
  children,
  footer,
  showHeader = true,
  headerTrailing,
}: OnboardingChatLayoutProps) {
  return (
    <div className="font-display relative flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[#FFFFFF] text-[#0F0F12] antialiased selection:bg-[#E878BE]/18 selection:text-[#0F0F12]">
      {/*
        Full-viewport fixed layers must start below RequireAuth’s PublicNav (~4rem), or they paint
        over the logo / email / sign out bar.
      */}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 top-16 z-0">
        <div className="absolute inset-0 bg-[#FFFFFF]" />
        <div className="absolute inset-0 opacity-[0.5]" style={gridBgStyle} />
      </div>

      <div className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col items-center px-4 py-3 sm:px-6 sm:py-4">
        <div
          className={
            "flex h-full w-full max-w-[720px] min-h-0 flex-1 flex-col overflow-hidden rounded-[1.35rem] " +
            "border border-zinc-200/80 bg-white shadow-[0_20px_50px_-28px_rgba(15,23,42,0.12)] " +
            "ring-1 ring-zinc-950/[0.03]"
          }
        >
          {showHeader ? <ChatHeader trailing={headerTrailing} /> : null}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-gradient-to-b from-zinc-50/80 to-white">
            {children}
          </div>
          {footer ? (
            <div className="shrink-0 border-t border-zinc-100/90 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm">
              {footer}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
