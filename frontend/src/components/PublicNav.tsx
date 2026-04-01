import { Link } from "react-router-dom";

type Props = {
  email?: string;
  onLogout?: () => void;
  /** When false, hide product nav to Connectors (e.g. during onboarding). */
  showConnectors?: boolean;
};

export default function PublicNav({ email, onLogout, showConnectors = false }: Props) {
  return (
    <header className="relative z-40 border-b border-stone-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link
          to="/app"
          className="flex items-center gap-2 text-lg font-semibold tracking-tight text-stone-900 no-underline"
          aria-label="Vector home"
        >
          <img src="/vector-logo.png" alt="" className="h-8 w-auto shrink-0" decoding="async" />
          Vector
        </Link>
        <nav className="flex items-center gap-6 text-sm font-medium text-stone-700">
          {showConnectors ? (
            <Link to="/app/connectors" className="no-underline hover:text-stone-950">
              Connectors
            </Link>
          ) : null}
          {email ? (
            <>
              <span className="max-w-[12rem] truncate text-stone-500" title={email}>
                {email}
              </span>
              {onLogout ? (
                <button
                  type="button"
                  className="cursor-pointer border-0 bg-transparent p-0 text-stone-700 underline decoration-stone-300 hover:text-stone-950"
                  onClick={onLogout}
                >
                  Sign out
                </button>
              ) : null}
            </>
          ) : (
            <Link to="/login" className="no-underline hover:text-stone-950">
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
