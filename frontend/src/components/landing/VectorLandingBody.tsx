import React, { type ReactNode, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import "../../styles/vector-landing-scoped.css";
import { MeetVectorIntegrationsHub } from "./MeetVectorIntegrationsHub.tsx";

const DEMO_CAL_URL = "https://calendar.app.google/GcS9iPFBuL9XFzhc8";

const PERCEPTION_CAPABILITIES = [
  {
    title: "Every signal, structured or human",
    sub: "Vector connects to any tool your team uses and reads beyond artifacts. Commits, tickets, but also Slack threads, call transcripts, and the decisions buried in conversations.",
  },
  {
    title: "Instant context, always available",
    sub: "The moment a pattern is captured, it is queryable. By your team, by any agent in your stack, at any time.",
  },
  {
    title: "A graph that compounds over time",
    sub: "Every new signal refines Vector's understanding of how your teams work. The longer it runs, the deeper the context.",
  },
] as const;

const FAQ_ITEMS: ReadonlyArray<{ q: string; a: ReactNode }> = [
  {
    q: "Who is Vector for?",
    a: (
      <p>
        CTOs and engineering leaders running teams where AI is already embedded in the shipping cycle. If your
        agents are writing, reviewing, and shipping code but your org&apos;s conventions and decisions
        aren&apos;t in the loop, Vector is built for you.
      </p>
    ),
  },
  {
    q: "What does Vector connect to?",
    a: (
      <p>
        GitHub, Linear, Slack, Notion, Google Drive, and call transcripts — with new integrations shipping every
        week. Vector reads across both structured data and human signals to build the execution graph. No new
        tools required, no behavior change for your team.
      </p>
    ),
  },
  {
    q: "Do we need to change how our team works?",
    a: (
      <p>
        No. Vector plugs into your existing stack and observes how your team already operates. There is no new
        workflow, no new interface, nothing to adopt.
      </p>
    ),
  },
  {
    q: "How is Vector different from a RAG system or a Claude agent we could build ourselves?",
    a: (
      <p>
        Building the retrieval layer is straightforward. The hard part is knowing which signals matter, how to
        extract decisions from unstructured conversations, and how to model execution patterns across an
        engineering org over time. That&apos;s Vector&apos;s core product. You&apos;re not buying an LLM wrapper.
        You&apos;re buying a model that understands how your org works.
      </p>
    ),
  },
  {
    q: "Does Vector read our Slack messages?",
    a: (
      <>
        <p>
          Yes, public channels only. Most execution decisions don&apos;t show up in tickets. They surface in
          threads, calls, and conversations.
        </p>
        <p>Private messages are never in scope and remain private.</p>
      </>
    ),
  },
  {
    q: "Does Vector track individual performance?",
    a: (
      <p>
        No. Vector tracks coordination patterns and execution signals at the team level. It does not score
        individuals, rank engineers, or produce performance ratings.
      </p>
    ),
  },
  {
    q: "Who owns the data?",
    a: (
      <p>
        You do. Vector acts as a data processor on your behalf. Your data is never used to train LLMs, internal
        models, or any other system. Contractually guaranteed. Processing can be paused or terminated at any
        time.
      </p>
    ),
  },
];

const IMPACT_BLOCKS = [
  {
    accent: true,
    stat: "42%",
    copy: "of coding time lost to context gaps. Not to meetings. Not to bugs. Just to ramping back up after every switch.",
  },
  {
    accent: false,
    stat: "4.4h",
    copy: "saved per senior engineer per week. When context is available. Right now, it isn't.",
  },
  {
    accent: true,
    stat: "3.2x",
    copy: "more technical debt when agents work without context. They reintroduce the patterns your team already rejected.",
  },
] as const;

function ValuePillarCapabilityGrid({ items }: { items: readonly { title: string; sub: string }[] }) {
  const cards = [
    {
      visual: (
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "16px",
            padding: "16px",
            border: "1px solid #F0F0F0",
            borderRadius: "10px",
            background: "#FAFAFA",
            fontSize: "11px",
          }}
        >
          <div style={{ flex: 1 }}>
            <div
              style={{
                color: "#AAAAAA",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "8px",
                fontSize: "10px",
              }}
            >
              Structured
            </div>
            <div
              style={{
                background: "#fff",
                border: "1px solid #EEEEEE",
                borderRadius: "6px",
                padding: "6px 8px",
                marginBottom: "6px",
                color: "#333",
                fontSize: "11px",
              }}
            >
              PR #214 merged
            </div>
            <div
              style={{
                background: "#fff",
                border: "1px solid #EEEEEE",
                borderRadius: "6px",
                padding: "6px 8px",
                color: "#333",
                fontSize: "11px",
              }}
            >
              PAY-640 in review
            </div>
          </div>
          <div
            style={{
              width: "1px",
              background: "#E878BE",
              opacity: 0.3,
              flexShrink: 0,
            }}
          />
          <div style={{ flex: 1 }}>
            <div
              style={{
                color: "#AAAAAA",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "8px",
                fontSize: "10px",
              }}
            >
              Human
            </div>
            <div
              style={{
                background: "#fff",
                border: "1px solid #EEEEEE",
                borderRadius: "6px",
                padding: "6px 8px",
                color: "#333",
                fontSize: "11px",
                lineHeight: 1.4,
              }}
            >
              <span style={{ color: "#E878BE" }}>@alex</span> we decided to drop the retry lib
            </div>
          </div>
        </div>
      ),
    },
    {
      visual: (
        <div
          style={{
            marginBottom: "16px",
            padding: "16px",
            border: "1px solid #F0F0F0",
            borderRadius: "10px",
            background: "#FAFAFA",
            fontSize: "11px",
          }}
        >
          <div
            style={{
              background: "#fff",
              border: "1px solid #EEEEEE",
              borderRadius: "6px",
              padding: "8px 10px",
              marginBottom: "8px",
              color: "#333",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span style={{ color: "#AAAAAA", fontSize: "10px" }}>Query</span>
            <span>What error-handling pattern do we use?</span>
            <span
              style={{
                display: "inline-block",
                width: "2px",
                height: "12px",
                background: "#E878BE",
                animation: "blink 1s step-end infinite",
                marginLeft: "2px",
              }}
            />
          </div>
          <div
            style={{
              background: "#FFF0F8",
              border: "1px solid #FFB3D9",
              borderRadius: "6px",
              padding: "8px 10px",
              color: "#333",
              lineHeight: 1.5,
            }}
          >
            Exponential backoff — decided in <span style={{ color: "#E878BE" }}>#payments</span>, March 2026
          </div>
        </div>
      ),
    },
    {
      visual: (
        <div
          style={{
            marginBottom: "16px",
            padding: "16px",
            border: "1px solid #F0F0F0",
            borderRadius: "10px",
            background: "#FAFAFA",
            height: "120px",
            display: "flex",
            alignItems: "flex-end",
            gap: "12px",
            justifyContent: "center",
          }}
        >
          {[
            { label: "Week 1", height: "30%", opacity: 0.3 },
            { label: "Week 4", height: "60%", opacity: 0.6 },
            { label: "Week 12", height: "90%", opacity: 1 },
          ].map((bar) => (
            <div
              key={bar.label}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "6px",
                flex: 1,
                height: "100%",
                justifyContent: "flex-end",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: bar.height,
                  background: "#E878BE",
                  opacity: bar.opacity,
                  borderRadius: "4px 4px 0 0",
                  transition: "height 0.3s ease",
                }}
              />
              <div
                style={{
                  fontSize: "10px",
                  fontWeight: 600,
                  color: "#333",
                  whiteSpace: "nowrap",
                }}
              >
                {bar.label}
              </div>
            </div>
          ))}
        </div>
      ),
    },
  ];

  return (
    <ul
      className="empower-cap-list empower-cap-list--grid"
      aria-label="Capabilities"
      style={{ listStyle: "none", padding: 0, margin: 0 }}
    >
      {items.map((item, i) => (
        <li
          key={item.title}
          style={{
            border: "1px solid #EEEEEE",
            borderRadius: "12px",
            padding: "24px",
            background: "#ffffff",
          }}
        >
          {cards[i]?.visual}
          <span
            style={{
              display: "block",
              fontWeight: 700,
              fontSize: "15px",
              color: "#111111",
              marginBottom: "8px",
            }}
          >
            {item.title}
          </span>
          <span
            style={{
              display: "block",
              fontSize: "13px",
              color: "#666666",
              lineHeight: 1.6,
            }}
          >
            {item.sub}
          </span>
        </li>
      ))}
    </ul>
  );
}

function useRevealInViewRef() {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.classList.add("is-inview");
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-inview");
            obs.unobserve(entry.target);
          }
        }
      },
      { root: null, rootMargin: "0px 0px -6% 0px", threshold: 0.1 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

type ImpactBlock = (typeof IMPACT_BLOCKS)[number];

function AnimatedImpactColumn({ block }: { block: ImpactBlock }) {
  const colRef = useRevealInViewRef();
  const [displayed, setDisplayed] = useState("0");
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const el = colRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !animated) {
            setAnimated(true);
            obs.unobserve(entry.target);
            const raw = block.stat;
            const num = parseFloat(raw);
            const suffix = raw.replace(String(num), "");
            const duration = 1800;
            const steps = 60;
            const interval = duration / steps;
            let step = 0;
            const timer = setInterval(() => {
              step++;
              const progress = step / steps;
              const eased = 1 - Math.pow(1 - progress, 3);
              const current = num * eased;
              const decimals = raw.includes(".") ? 1 : 0;
              setDisplayed(current.toFixed(decimals) + suffix);
              if (step >= steps) {
                clearInterval(timer);
                setDisplayed(raw);
              }
            }, interval);
          }
        }
      },
      { threshold: 0.3 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [animated, block.stat]);

  return (
    <article ref={colRef} className="impact-strip__col">
      <p className={`impact-strip__stat${block.accent ? " impact-strip__stat--accent" : ""}`}>{displayed}</p>
      <p className="impact-strip__copy">{block.copy}</p>
    </article>
  );
}

export type VectorLandingSignedCta = { to: string; label: string };

type VectorLandingBodyProps = {
  /** When set, bottom CTA becomes entry to the product instead of the join waitlist link. */
  signedInWorkspaceCta?: VectorLandingSignedCta;
};

function FaqTwoCol({ items }: { items: ReadonlyArray<{ q: string; a: ReactNode }> }) {
  const [active, setActive] = React.useState(0);
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "48px",
        alignItems: "start",
      }}
    >
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: "4px",
        }}
      >
        {items.map((item, i) => (
          <li key={item.q}>
            <button
              type="button"
              onClick={() => setActive(i)}
              style={{
                width: "100%",
                textAlign: "left",
                background: active === i ? "#FFF0F8" : "transparent",
                border: "none",
                cursor: "pointer",
                padding: "14px 16px",
                borderRadius: "8px",
                fontSize: "15px",
                fontWeight: active === i ? 600 : 400,
                color: active === i ? "#111111" : "#666666",
                borderLeft: active === i ? "2px solid #E878BE" : "2px solid transparent",
                transition: "all 0.15s ease",
              }}
            >
              {item.q}
            </button>
          </li>
        ))}
      </ul>

      <div
        style={{
          padding: "24px 32px",
          border: "1px solid #F0F0F0",
          borderRadius: "12px",
          background: "#FAFAFA",
          fontSize: "15px",
          color: "#444444",
          lineHeight: 1.7,
          minHeight: "160px",
        }}
      >
        <p
          style={{
            fontSize: "13px",
            fontWeight: 700,
            color: "#E878BE",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            margin: 0,
            marginBottom: "12px",
          }}
        >
          {items[active].q}
        </p>
        <div style={{ color: "#444444" }}>{items[active].a}</div>
      </div>
    </div>
  );
}

export function VectorLandingBody({ signedInWorkspaceCta }: VectorLandingBodyProps) {
  return (
    <div id="vector-landing">
      <div className="page-bg" aria-hidden="true">
        <div className="page-bg__solid" />
        <div className="page-bg__grid" />
      </div>

      <main>
        <div className="wrap hero hero--centered">
          <div className="hero-centered-shell">
            <div className="hero-copy hero-copy--centered">
              <h1>
                <span className="hero-headline-line">
                  Agents don&apos;t inherit context. <span className="accent">Vector does.</span>
                </span>
              </h1>
              <p className="sub hero-sub hero-sub--centered">
                Build a persistent understanding of how your teams ship, and make it queryable by humans and agents
                alike.
              </p>
              <div className="hero-cta-row hero-cta-row--centered">
                <a className="btn-light" href={DEMO_CAL_URL} target="_blank" rel="noopener noreferrer">
                  Book a demo
                </a>
              </div>
            </div>

            <div className="hero-marquee" aria-hidden="true">
              <div className="hero-marquee__track">
                {[
                  { slug: "notion", label: "Notion" },
                  { slug: "slack", label: "Slack" },
                  { slug: "linear", label: "Linear" },
                  { slug: "github", label: "GitHub" },
                  { slug: "google", label: "Google" },
                  { slug: "googlegemini", label: "Google Gemini" },
                  { slug: "sentry", label: "Sentry" },
                  { slug: "notion", label: "Notion" },
                  { slug: "slack", label: "Slack" },
                  { slug: "linear", label: "Linear" },
                  { slug: "github", label: "GitHub" },
                  { slug: "google", label: "Google" },
                  { slug: "googlegemini", label: "Google Gemini" },
                  { slug: "sentry", label: "Sentry" },
                ].map((tool, i) => (
                  <div key={i} className="hero-marquee__item">
                    <img
                      src={`https://raw.githubusercontent.com/simple-icons/simple-icons/11.6.0/icons/${tool.slug}.svg`}
                      width={20}
                      height={20}
                      alt={tool.label}
                      style={{ filter: "invert(0.4)" }}
                    />
                    <span className="hero-marquee__label">{tool.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="hero-divider" aria-hidden="true" />

        <section className="section" id="meet-vector" aria-labelledby="meet-vector-heading">
          <div className="container">
            <div className="meet-vector-layout">
              <div className="meet-vector-copy">
                <h2 id="meet-vector-heading">
                  Meet <span className="accent">Vector</span>
                </h2>
                <p className="sub meet-vector__sub">
                  The ground truth layer for your engineering.
                </p>
                <p className="sub meet-vector__support">
                  Vector is a living execution graph of your org, extracting hidden insights from structured data and human signals across your entire stack. Queryable by your team and every agent in it.
                </p>
              </div>
              <MeetVectorIntegrationsHub />
            </div>
          </div>
        </section>

        <section className="join-strip" id="join-strip" aria-labelledby="join-strip-heading">
          <div className="join-strip__inner">
            <h2 id="join-strip-heading" className="join-strip__heading">
              Close the <span className="accent">context gap.</span>
            </h2>
            <div className="join-strip__cta">
              {signedInWorkspaceCta ? (
                <Link
                  className="btn-pill btn-pill--hero btn-pill--join-list"
                  to={signedInWorkspaceCta.to}
                >
                  {signedInWorkspaceCta.label}
                </Link>
              ) : (
                <Link className="btn-pill btn-pill--hero btn-pill--join-list" to="/signup">
                  Start now
                </Link>
              )}
            </div>
          </div>
        </section>

        <div id="core-features" className="core-features-group">
          <section className="section" aria-labelledby="value-pillar-perception-heading">
            <div className="section-inner value-pillars">
              <div className="value-pillar">
                <header className="value-pillar__header text-center">
                  <h2 id="value-pillar-perception-heading">
                    How Vector builds <span className="accent">your execution graph</span>
                  </h2>
                </header>
                <div className="value-pillar-features">
                  <ValuePillarCapabilityGrid items={PERCEPTION_CAPABILITIES} />
                </div>
              </div>
            </div>
          </section>
        </div>

        <section className="impact-strip" id="impact" aria-label="What changes when Vector runs coordination">
          <div className="impact-strip__inner">
            <div className="impact-strip__row">
              {IMPACT_BLOCKS.map((block) => (
                <AnimatedImpactColumn key={block.stat} block={block} />
              ))}
            </div>
          </div>
        </section>

        <div className="hero-divider" aria-hidden="true" />

        <section className="section" id="security" aria-labelledby="security-heading">
          <div className="section-inner">
            <header className="text-center" style={{ marginBottom: "48px" }}>
              <h2 id="security-heading">
                Your data <span className="accent">stays yours.</span>
              </h2>
            </header>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: "24px",
                maxWidth: "860px",
                margin: "0 auto",
              }}
            >
              {[
                {
                  icon: (
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#E878BE"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  ),
                  title: "Never used for training",
                  body: "Your data is never used to train LLMs, internal models, or any other system. Contractually guaranteed.",
                },
                {
                  icon: (
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#E878BE"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                  ),
                  title: "Suspend or delete at any time",
                  body: "Data processing can be paused on request, no questions asked. All data removed automatically when your contract ends.",
                },
                {
                  icon: (
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#E878BE"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <circle cx="12" cy="12" r="10" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  ),
                  title: "Engineering signals only",
                  body: "Vector never touches Slack DMs, customer PII, financial records, or HR data. Work tools only, nothing else.",
                },
                {
                  icon: (
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#E878BE"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                      <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                      <line x1="6" y1="6" x2="6.01" y2="6" />
                      <line x1="6" y1="18" x2="6.01" y2="18" />
                    </svg>
                  ),
                  title: "AWS Ireland. Encrypted end to end.",
                  body: "AES-256 at rest, TLS 1.2+ in transit. GDPR compliant. SOC 2 in progress.",
                },
              ].map((block) => (
                <div
                  key={block.title}
                  style={{
                    border: "1px solid #E8E8E8",
                    borderRadius: "12px",
                    padding: "28px 32px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <div style={{ marginBottom: "4px" }}>{block.icon}</div>
                  <p
                    style={{
                      fontSize: "16px",
                      fontWeight: 700,
                      color: "#111111",
                      margin: 0,
                    }}
                  >
                    {block.title}
                  </p>
                  <p
                    style={{
                      fontSize: "14px",
                      color: "#555555",
                      lineHeight: 1.6,
                      margin: 0,
                    }}
                  >
                    {block.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="cta">
          <div className="section-inner">
            <div className="cta-card">
              <h2>
                Try <span className="accent">Vector</span> now.
              </h2>
              <ol className="cta-steps">
                <li>
                  <span className="cta-num">1</span>
                  <span className="cta-step-copy">Connect your stack</span>
                </li>
                <li>
                  <span className="cta-num">2</span>
                  <span className="cta-step-copy">Vector builds your execution graph</span>
                </li>
                <li>
                  <span className="cta-num">3</span>
                  <span className="cta-step-copy">Get the context your teams and agents have been missing</span>
                </li>
              </ol>
              <div className="cta-actions">
                {signedInWorkspaceCta ? (
                  <Link
                    className="btn-pill btn-pill--hero btn-pill--join-list"
                    to={signedInWorkspaceCta.to}
                  >
                    {signedInWorkspaceCta.label}
                  </Link>
                ) : (
                  <Link className="btn-pill btn-pill--hero btn-pill--join-list" to="/signup">
                    join
                  </Link>
                )}
                <a className="btn-light" href={DEMO_CAL_URL} target="_blank" rel="noopener noreferrer">
                  Book a demo
                </a>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="faq" aria-labelledby="faq-heading">
          <div className="section-inner">
            <header style={{ marginBottom: "48px" }}>
              <h2 id="faq-heading">
                Frequently asked <span className="accent">questions</span>
              </h2>
            </header>
            <FaqTwoCol items={FAQ_ITEMS} />
          </div>
        </section>
      </main>

      <footer>
        <p>© {new Date().getFullYear()} Vector</p>
      </footer>
    </div>
  );
}
