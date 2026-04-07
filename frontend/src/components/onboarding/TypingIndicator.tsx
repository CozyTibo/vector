import ChatAvatar from "./ChatAvatar";
import { landingAccentText } from "../landing/landingBrandPalette";

export default function TypingIndicator() {
  return (
    <div className="onboarding-message-enter flex gap-3 px-3 py-1.5 sm:gap-3.5">
      <ChatAvatar variant="vector" />
      {/*
        items-start + w-fit: default flex-col stretch was making the typing pill span the full chat
        width and left huge empty space beside the dots.
      */}
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
        <span className={`text-[11px] font-semibold ${landingAccentText}`}>Vector</span>
        <div
          className={
            "inline-flex w-fit max-w-[min(100%,32rem)] shrink-0 items-center gap-1.5 rounded-2xl rounded-tl-md " +
            "border border-zinc-200/85 bg-white/95 px-4 py-2.5 shadow-[0_12px_32px_-22px_rgba(15,23,42,0.35)] " +
            "ring-1 ring-zinc-950/[0.04]"
          }
        >
          <span className="sr-only">Vector is typing</span>
          <span className="inline-flex items-center gap-1.5">
            <span className="onboarding-typing-dot h-2 w-2 rounded-full bg-[#E878BE] [animation-delay:-0.2s]" />
            <span className="onboarding-typing-dot h-2 w-2 rounded-full bg-[#E878BE] [animation-delay:-0.1s]" />
            <span className="onboarding-typing-dot h-2 w-2 rounded-full bg-[#E878BE]" />
          </span>
        </div>
      </div>
    </div>
  );
}
