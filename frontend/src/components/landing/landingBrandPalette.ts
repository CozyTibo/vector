/**
 * Lighter marketing accent (replaces legacy deep magenta #C0009A).
 * Keeps headline gradients readable on white while feeling like soft pink.
 */
export const landingAccentRgb = "232, 120, 190";

/** Headline keyword spans — end stop stays saturated so long words (e.g. “strategy”) stay legible on white */
export const landingTitleKeywordGradient =
  "bg-gradient-to-r from-[#BE5E94] via-[#E888C4] to-[#C86898] bg-clip-text text-transparent";

/** Thin horizontal rails (tabs, persona card caps) */
export const landingSubtleLineH =
  "bg-gradient-to-r from-[#BE5E94] via-[#E878BE] to-[#BE5E94]";

/** Thin vertical rail (hero Vector message bubbles) */
export const landingSubtleLineV =
  "bg-gradient-to-b from-[#BE5E94] via-[#E878BE] to-[#BE5E94]";

/** Solid accent for labels, tabs, icons, inline highlights */
export const landingAccentText = "text-[#E878BE]";

/** Purple-style tool chip on diagram */
export const landingAccentChipPurple =
  "border-[#E878BE]/40 bg-[#E878BE]/10 text-pink-800";
