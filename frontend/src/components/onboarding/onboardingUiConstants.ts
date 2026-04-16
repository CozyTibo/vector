/**
 * Shared onboarding surface styles (connector steps, marketing waitlist chat, etc.)
 * so CTA cards stay visually aligned with the product onboarding shell.
 */

export const CONNECTOR_STEP_FOOTER_LINK_CLASS =
  "text-center text-sm leading-snug text-zinc-500 underline decoration-zinc-300 decoration-1 underline-offset-2 hover:text-zinc-700";

/** Pink-bordered card used above the fold on connector CTAs (e.g. Connect Slack). */
export const ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS =
  "rounded-2xl border border-[#E878BE]/20 bg-white/95 p-6 text-center shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04]";

/** Primary gradient control styled as a link (`<a>` / `<Link>`). */
export const ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS =
  "inline-flex rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white no-underline shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]";

/** Primary gradient `<button>` (add disabled:… at call site as needed). */
export const ONBOARDING_PRIMARY_CTA_GRADIENT_BUTTON_CLASS =
  "rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]";
