import { Link } from "react-router-dom";

import vectorLogoUrl from "../../assets/vector-logo.png";

type Props = {
  children: React.ReactNode;
  /** When false, only background + font (e.g. nested use). Default shows top chrome. */
  showChrome?: boolean;
  /** When true, skip the fixed marketing grid (e.g. home uses vector-landing’s own backdrop). */
  bareBackground?: boolean;
};

export default function MarketingLayout({ children, showChrome = true, bareBackground = false }: Props) {
  return (
    <div className="font-display relative min-h-screen overflow-x-hidden bg-[#FFFFFF] text-[#0F0F12] antialiased selection:bg-[#E878BE]/18 selection:text-[#0F0F12]">
      {!bareBackground ? (
        <div className="pointer-events-none fixed inset-0">
          <div className="absolute inset-0 bg-[#FFFFFF]" />
          <div
            className="absolute inset-0 opacity-[0.5]"
            style={{
              backgroundImage: `
              linear-gradient(rgba(15,15,18,0.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(15,15,18,0.05) 1px, transparent 1px)
            `,
              backgroundSize: "72px 72px",
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
            <img
              src={vectorLogoUrl}
              alt=""
              className="h-9 w-auto shrink-0 transition-transform duration-300 group-hover:scale-105 sm:h-10"
              decoding="async"
            />
            <span className="text-lg font-semibold tracking-tight text-[#0F0F12] sm:text-xl">Vector</span>
          </Link>
          <nav className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/login"
              className="rounded-full px-4 py-2 text-sm font-medium text-zinc-600 no-underline transition-colors hover:text-[#0F0F12]"
            >
              Sign in
            </Link>
            <Link
              to="/signup"
              className="rounded-full bg-[#0F0F12] px-4 py-2 text-sm font-semibold text-white no-underline shadow-[0_6px_20px_-8px_rgba(15,23,42,0.35)] transition-[transform,box-shadow] hover:scale-[1.02] hover:shadow-[0_8px_28px_-8px_rgba(15,23,42,0.25)] sm:px-5"
            >
              Get started
            </Link>
          </nav>
        </header>
      ) : null}

      <div className="relative z-10">{children}</div>
    </div>
  );
}
