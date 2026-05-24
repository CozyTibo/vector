import type { CSSProperties } from "react";

const SI_ICON_BASE =
  "https://raw.githubusercontent.com/simple-icons/simple-icons/11.6.0/icons";

const INTEGRATION_TOOLS = [
  { slug: "notion", label: "Notion" },
  { slug: "slack", label: "Slack" },
  { slug: "linear", label: "Linear" },
  { slug: "github", label: "GitHub" },
  { slug: "google", label: "Google" },
  { slug: "googlegemini", label: "Google Gemini" },
  { slug: "sentry", label: "Sentry" },
];

export function MeetVectorIntegrationsHub() {
  return (
    <aside
      aria-label="Vector connects to the tools your team already uses"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0",
        padding: "40px 32px",
        background: "#ffffff",
        borderRadius: "16px",
        border: "1px solid #F0F0F0",
        width: "100%",
        maxWidth: "400px",
        position: "relative",
      }}
    >
      {/* Tool logos — top row */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          flexWrap: "nowrap",
          gap: "8px",
          marginBottom: "20px",
          position: "relative",
          zIndex: 1,
        }}
      >
        {INTEGRATION_TOOLS.map((tool) => (
          <div
            key={tool.slug}
            title={tool.label}
            style={{
              width: "40px",
              height: "40px",
              border: "1px solid #E8E8E8",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "#FAFAFA",
            }}
          >
            <img
              src={`${SI_ICON_BASE}/${tool.slug}.svg`}
              width={18}
              height={18}
              alt={tool.label}
              style={{ filter: "invert(0.6)" }}
              loading="lazy"
            />
          </div>
        ))}
      </div>

      {/* Arrows down from tools to Vector */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "32px",
          marginBottom: "12px",
          position: "relative",
          zIndex: 1,
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <div
              style={{
                width: "1px",
                height: "24px",
                background: "linear-gradient(to bottom, #E878BE, rgba(232,120,190,0.2))",
              }}
            />
            <div
              style={{
                width: 0,
                height: 0,
                borderLeft: "3px solid transparent",
                borderRight: "3px solid transparent",
                borderTop: "4px solid rgba(232,120,190,0.5)",
              }}
            />
          </div>
        ))}
      </div>

      {/* Vector layer */}
      <div
        style={{
          position: "relative",
          zIndex: 1,
          background: "#FFF0F8",
          border: "1px solid #FFB3D9",
          borderRadius: "10px",
          padding: "18px 32px",
          textAlign: "center",
          width: "100%",
          marginBottom: "12px",
        }}
      >
        <div
          style={{
            color: "#E878BE",
            fontSize: "13px",
            letterSpacing: "0.15em",
            textTransform: "uppercase",
            fontWeight: 700,
            marginBottom: "4px",
          }}
        >
          VECTOR
        </div>
        <div
          style={{
            color: "#AAAAAA",
            fontSize: "11px",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          Persistent Context Layer
        </div>
      </div>

      {/* Arrow down to agent */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          marginBottom: "12px",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div
          style={{
            width: "1px",
            height: "24px",
            background: "linear-gradient(to bottom, #E878BE, rgba(232,120,190,0.2))",
          }}
        />
        <div
          style={{
            width: 0,
            height: 0,
            borderLeft: "3px solid transparent",
            borderRight: "3px solid transparent",
            borderTop: "4px solid rgba(232,120,190,0.5)",
          }}
        />
      </div>

      {/* Bottom label */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "8px",
          position: "relative",
          zIndex: 1,
        }}
      >
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <line x1="16" y1="2" x2="16" y2="30" stroke="#E878BE" strokeWidth="1.5" />
          <line x1="2" y1="16" x2="30" y2="16" stroke="#E878BE" strokeWidth="1.5" />
          <line x1="6" y1="6" x2="26" y2="26" stroke="#E878BE" strokeWidth="1.5" />
          <line x1="26" y1="6" x2="6" y2="26" stroke="#E878BE" strokeWidth="1.5" />
          <line x1="3" y1="11" x2="29" y2="21" stroke="#E878BE" strokeWidth="0.75" opacity="0.5" />
          <line x1="11" y1="3" x2="21" y2="29" stroke="#E878BE" strokeWidth="0.75" opacity="0.5" />
          <line x1="29" y1="11" x2="3" y2="21" stroke="#E878BE" strokeWidth="0.75" opacity="0.5" />
          <line x1="21" y1="3" x2="11" y2="29" stroke="#E878BE" strokeWidth="0.75" opacity="0.5" />
        </svg>
        <div
          style={{
            color: "#E878BE",
            fontSize: "11px",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            textAlign: "center",
          }}
        >
          The agents you run.
          <br />
          The humans who decide.
        </div>
      </div>
    </aside>
  );
}
