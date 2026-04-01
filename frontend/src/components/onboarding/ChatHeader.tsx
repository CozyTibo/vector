import vectorHeroAvatarUrl from "../../assets/vector-hero-avatar.png";
import { landingAccentText } from "../landing/landingBrandPalette";

/**
 * In-card header — teammate DM identity (matches landing hero Vector treatment).
 */
export default function ChatHeader() {
  return (
    <header className="shrink-0 border-b border-zinc-100/95 bg-white/90 px-4 py-3.5 sm:px-5">
      <div className="flex items-center gap-3">
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
    </header>
  );
}
