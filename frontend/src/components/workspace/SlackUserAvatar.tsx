function initialsFromDisplayName(name: string): string {
  const t = name.trim();
  if (!t) {
    return "?";
  }
  const parts = t.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase().slice(0, 2);
  }
  return t.slice(0, 2).toUpperCase();
}

type SlackUserAvatarProps = {
  imageUrl: string | null | undefined;
  /** Display name or @handle — used for initials fallback and alt text. */
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const frame: Record<NonNullable<SlackUserAvatarProps["size"]>, string> = {
  sm: "h-7 w-7 text-[11px]",
  md: "h-9 w-9 text-[12px]",
  lg: "h-10 w-10 text-[13px]",
};

/**
 * Slack profile photo when available; otherwise initials on a neutral tile (matches onboarding pickers).
 */
export default function SlackUserAvatar({ imageUrl, name, size = "md", className = "" }: SlackUserAvatarProps) {
  const box = `${frame[size]} shrink-0 rounded-md object-cover ${className}`.trim();
  const initials = initialsFromDisplayName(name);

  if (imageUrl) {
    return <img src={imageUrl} alt="" className={box} loading="lazy" decoding="async" />;
  }

  return (
    <span
      className={`flex items-center justify-center rounded-md bg-zinc-200/80 font-semibold text-zinc-600 ${frame[size]} ${className}`.trim()}
      aria-hidden
    >
      {initials}
    </span>
  );
}
