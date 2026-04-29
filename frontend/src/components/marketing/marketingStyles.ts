/**
 * Tailwind class bundles aligned with `vector-landing-scoped.css` (#vector-landing):
 * Outfit via `font-display` on the layout root, --ink #0f0f12, --muted #52525b, --accent #e878be.
 */

export const marketingCard =
  "rounded-[1.75rem] border border-zinc-200/90 bg-white/80 p-8 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.12),inset_0_0_0_1px_rgba(232,120,190,0.05)] backdrop-blur-xl sm:p-10";

/** In-app panels (connectors grid, workspace signals) — same elevation as connector tiles. */
export const marketingSurfaceCard =
  "rounded-2xl border border-zinc-200/90 bg-white/90 shadow-[0_12px_40px_-28px_rgba(15,23,42,0.14)] ring-1 ring-zinc-950/[0.03]";

/** Workspace hub: flat surfaces, no drop shadow — modern, low-noise panels. */
export const workspaceFlatPanel = "rounded-2xl border border-zinc-100 bg-white";

/** Large thank-you / waitlist panel */
export const marketingCardLg =
  "rounded-[2rem] border border-zinc-200/90 bg-white/80 p-10 shadow-[0_32px_100px_-40px_rgba(15,23,42,0.14),inset_0_0_0_1px_rgba(232,120,190,0.05)] backdrop-blur-xl sm:p-14 lg:p-16";

export const marketingKicker =
  "text-xs font-semibold uppercase tracking-[0.16em] text-[#E878BE] sm:text-sm";

export const marketingPageTitle =
  "text-3xl font-semibold tracking-tight text-[#0F0F12] sm:text-4xl";

export const marketingSectionTitle =
  "text-2xl font-semibold tracking-tight text-[#0F0F12] sm:text-3xl";

export const marketingBody =
  "text-base leading-relaxed text-[#52525B] sm:text-lg sm:leading-relaxed";

export const marketingBodyLarge =
  "text-lg leading-relaxed text-[#52525B] sm:text-xl sm:leading-relaxed lg:text-2xl lg:leading-snug";

export const marketingAccentLink =
  "font-semibold text-[#E878BE] no-underline transition-colors hover:text-[#df6aad]";

export const marketingMutedLink =
  "text-sm font-medium text-[#52525B] no-underline transition-colors hover:text-[#0F0F12]";

export const marketingLabel = "mt-6 block text-sm font-semibold text-[#0F0F12]";

export const marketingLabelTight = "mt-4 block text-sm font-semibold text-[#0F0F12]";

export const marketingField =
  "mt-2 w-full rounded-2xl border border-zinc-200/90 bg-white/90 px-4 py-3.5 text-[#0F0F12] outline-none placeholder:text-zinc-400 transition-[border-color,box-shadow] focus:border-[#E878BE]/55 focus:shadow-[0_0_0_3px_rgba(232,120,190,0.22)]";

/** Primary CTA — pink “Join the list” (landing `.btn-pill--hero.btn-pill--join-list`). */
export const marketingBtnPrimaryPink =
  "w-full rounded-full bg-[#E878BE] py-3.5 text-sm font-semibold text-white shadow-[0_12px_32px_-16px_rgba(232,120,190,0.55)] transition-[transform,background-color] hover:scale-[1.01] hover:bg-[#df6aad] disabled:cursor-not-allowed disabled:opacity-50";
