import vectorHeroAvatarUrl from "../../assets/vector-white-bg.png";

type ChatAvatarProps = {
  variant: "vector" | "user";
  /** User initials (1–2 chars), e.g. "TH" */
  userInitials?: string;
  className?: string;
};

export default function ChatAvatar({ variant, userInitials = "?", className = "" }: ChatAvatarProps) {
  if (variant === "vector") {
    return (
      <span
        className={
          `inline-flex h-10 w-10 shrink-0 overflow-hidden rounded-2xl bg-zinc-50 shadow-md ring-2 ring-[#F5C8E0]/90 ${className}`
        }
      >
        <img
          src={vectorHeroAvatarUrl}
          alt=""
          className="h-full w-full object-cover object-center"
          width={40}
          height={40}
          decoding="async"
        />
      </span>
    );
  }
  return (
    <span
      className={
        `inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-zinc-100 text-[13px] font-semibold ` +
        `text-zinc-700 shadow-sm ring-1 ring-zinc-200/90 ${className}`
      }
      aria-hidden
    >
      {userInitials.slice(0, 2).toUpperCase()}
    </span>
  );
}
