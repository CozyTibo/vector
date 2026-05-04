import type { CSSProperties } from "react";

import vectorWhiteBgUrl from "../../assets/logo.jpeg";

/** Simple Icons v11.6.0 SVGs (MIT): https://github.com/simple-icons/simple-icons */
const SI_ICON_BASE =
  "https://raw.githubusercontent.com/simple-icons/simple-icons/11.6.0/icons";

type Tool = { slug: string; label: string };

const INTEGRATION_TOOLS: Tool[] = [
  { slug: "notion", label: "Notion" },
  { slug: "slack", label: "Slack" },
  { slug: "linear", label: "Linear" },
  { slug: "google", label: "Google" },
  { slug: "github", label: "GitHub" },
  { slug: "googlegemini", label: "Google Gemini" },
  { slug: "sentry", label: "Sentry" },
];

function toolIconUrl(slug: string) {
  return `${SI_ICON_BASE}/${slug}.svg`;
}

function IntegrationMark({ tool, orbitIndex }: { tool: Tool; orbitIndex: number }) {
  return (
    <div
      className="meet-vector-hub__mark"
      style={{ "--orbit-index": orbitIndex } as CSSProperties}
      role="img"
      aria-label={tool.label}
    >
      <img
        className="meet-vector-hub__tool-icon"
        src={toolIconUrl(tool.slug)}
        width={32}
        height={32}
        alt=""
        loading="lazy"
        decoding="async"
      />
    </div>
  );
}

export function MeetVectorIntegrationsHub() {
  return (
    <aside
      className="meet-vector-hub"
      aria-label="Vector connects to the tools your team already uses"
    >
      <div
        className="meet-vector-hub__orbit"
        style={{ "--orbit-count": INTEGRATION_TOOLS.length } as CSSProperties}
      >
        <div className="meet-vector-hub__center">
          <img
            className="meet-vector-hub__vector"
            src={vectorWhiteBgUrl}
            width={180}
            height={180}
            alt="Vector"
          />
        </div>
        {INTEGRATION_TOOLS.map((t, i) => (
          <IntegrationMark key={t.slug} tool={t} orbitIndex={i} />
        ))}
      </div>
    </aside>
  );
}
