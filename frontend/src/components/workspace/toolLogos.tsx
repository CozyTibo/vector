/** Simple Icons (MIT) via jsDelivr — brand marks only. */
const LOGO_SRC: Record<string, string> = {
  github: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/github.svg",
  gitlab: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/gitlab.svg",
  linear: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/linear.svg",
  jira: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/jira.svg",
  slack: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/slack.svg",
  notion: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/notion.svg",
};

const logoWrap = "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-zinc-50 ring-1 ring-zinc-200/90";

export function ToolLogo({ toolId, name }: { toolId: string; name: string }) {
  const src = LOGO_SRC[toolId];
  if (!src) {
    return (
      <span className={`${logoWrap} text-sm font-semibold text-zinc-500`} aria-hidden>
        {name.slice(0, 1)}
      </span>
    );
  }
  return (
    <span className={logoWrap}>
      <img src={src} alt="" className="h-7 w-7 object-contain" loading="lazy" decoding="async" />
    </span>
  );
}
