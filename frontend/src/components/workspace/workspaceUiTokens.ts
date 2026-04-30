/**
 * Logged-in workspace UI — uses CSS variables from `.workspace-app` (RequireAuth).
 * Primary actions use `--color-action-primary` (+ hover/active); signals stay emerald/neutral (WorkspaceSignalsTab).
 */

export const workspaceSpinner =
  "h-5 w-5 animate-spin rounded-full border-2 border-zinc-200 border-t-zinc-700";

export const workspaceSpinnerMd =
  "h-7 w-7 animate-spin rounded-full border-2 border-zinc-200 border-t-zinc-700";

export const workspaceSpinnerLg =
  "h-8 w-8 animate-spin rounded-full border-2 border-zinc-200 border-t-zinc-700";

export const workspaceSpinnerHero =
  "h-9 w-9 animate-spin rounded-full border-2 border-zinc-200 border-t-zinc-700";

/** Top app nav — current route (neutral only; location ≠ action). */
export const workspaceNavLinkCurrent =
  "inline-block border-b-2 border-zinc-900 pb-0.5 text-sm font-semibold text-zinc-900 no-underline";

export const workspaceNavLinkRest =
  "text-sm font-medium text-zinc-500 no-underline transition-colors hover:text-zinc-800";

/** Auth gate link in app shell (loading) — action blue, not marketing pink. */
export const workspaceAuthGateLink =
  "font-semibold text-[color:var(--color-action-primary)] no-underline transition-colors hover:text-[color:var(--color-action-hover)]";

/** Signal bucket bar: live slot (semantic success, not brand pink). */
export const workspaceSignalBarActive = "bg-emerald-600";

/** Scan row: active slot glyph. */
export const workspaceSignalGlyphActive = "text-emerald-600";

const primaryInteractive =
  "shadow-sm transition-all hover:bg-[color:var(--color-action-hover)] active:bg-[color:var(--color-action-active)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-action-primary)]";

export const workspacePrimaryButton = `inline-flex w-full items-center justify-center rounded-lg bg-[color:var(--color-action-primary)] px-3 py-2 text-sm font-semibold text-white ${primaryInteractive}`;

export const workspacePrimaryButtonSm = `inline-flex items-center justify-center rounded-lg bg-[color:var(--color-action-primary)] px-3 py-1.5 text-xs font-semibold text-white ${primaryInteractive} sm:px-4 sm:py-2 sm:text-sm`;

/** Full-width / block primary (Connect, modal confirm). */
export const workspacePrimaryButtonBase = `rounded-lg bg-[color:var(--color-action-primary)] px-4 py-2.5 text-base font-semibold text-white ${primaryInteractive} disabled:opacity-40`;

/** Toolbar / inline primary (Add team, etc.). */
export const workspacePrimaryButtonToolbar = `inline-flex items-center justify-center rounded-lg bg-[color:var(--color-action-primary)] px-4 py-2.5 text-base font-semibold text-white ${primaryInteractive}`;

export const workspacePrimaryButtonCompact = `rounded-lg bg-[color:var(--color-action-primary)] px-4 py-2 text-sm font-semibold text-white ${primaryInteractive}`;

/** Secondary — Edit tools, Cancel, Add team when save is primary, etc. */
export const workspaceSecondaryButton =
  "inline-flex shrink-0 items-center justify-center rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-400";

export const workspaceSecondaryButtonBase =
  "rounded-lg border border-zinc-300 bg-white px-4 py-2.5 text-base font-semibold text-zinc-900 shadow-sm transition hover:bg-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-400";

/** Form fields — neutral focus (not brand). */
export const workspaceInputFocusRing =
  "focus:border-zinc-400 focus:shadow-[0_0_0_3px_rgba(63,63,70,0.12)]";
