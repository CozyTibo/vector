import { Link } from "react-router-dom";

type Props = {
  children: React.ReactNode;
  /** When false, only background + font (e.g. nested use). Default shows top chrome. */
  showChrome?: boolean;
};

export default function MarketingLayout({ children, showChrome = true }: Props) {
  return (
    <div className="font-display relative min-h-screen overflow-x-hidden bg-[#f5f4f1] text-zinc-900 antialiased selection:bg-violet-400/20 selection:text-zinc-900">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-white via-[#f5f4f1] to-[#eeeee9]" />
        <div className="absolute -left-[15%] top-[5%] h-[min(42vh,420px)] w-[min(42vw,420px)] rounded-full bg-violet-500 opacity-[0.09] blur-[100px]" />
        <div className="absolute -right-[10%] top-[25%] h-[min(38vh,380px)] w-[min(38vw,380px)] rounded-full bg-teal-400 opacity-[0.08] blur-[90px]" />
        <div className="absolute bottom-[10%] left-[35%] h-[min(35vh,360px)] w-[min(50vw,480px)] rounded-full bg-cyan-300 opacity-[0.07] blur-[110px]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_45%_at_50%_-5%,rgba(255,255,255,0.92),transparent)]" />
        <div
          className="absolute inset-0 opacity-[0.5]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(24,24,27,0.04) 1px, transparent 1px),
              linear-gradient(90deg, rgba(24,24,27,0.04) 1px, transparent 1px)
            `,
            backgroundSize: "72px 72px",
          }}
        />
      </div>

      {showChrome ? (
        <header className="relative z-20 mx-auto flex max-w-[96rem] items-center justify-between gap-4 px-5 pt-7 pb-4 sm:px-8 sm:pt-8">
          <Link
            to="/"
            className="group flex items-center gap-2.5 no-underline outline-none transition-opacity hover:opacity-90"
            aria-label="Vector home"
          >
            <img
              src="/vector-logo.png"
              alt=""
              className="h-9 w-auto shrink-0 transition-transform duration-300 group-hover:scale-105 sm:h-10"
              decoding="async"
            />
            <span className="text-lg font-semibold tracking-tight text-zinc-900 sm:text-xl">Vector</span>
          </Link>
          <nav className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/login"
              className="rounded-full px-4 py-2 text-sm font-medium text-zinc-600 no-underline transition-colors hover:text-zinc-900"
            >
              Sign in
            </Link>
            <Link
              to="/signup"
              className="rounded-full bg-zinc-900 px-4 py-2 text-sm font-semibold text-white no-underline shadow-[0_4px_24px_-6px_rgba(20,184,166,0.42),0_2px_8px_-4px_rgba(139,92,246,0.2)] transition-[transform,box-shadow] hover:scale-[1.02] hover:shadow-[0_6px_28px_-4px_rgba(6,182,212,0.32),0_2px_12px_-4px_rgba(124,58,237,0.22)] sm:px-5"
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
