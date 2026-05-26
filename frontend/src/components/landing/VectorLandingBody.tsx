import React, { type ReactNode, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import vectorHeroAvatarUrl from "../../assets/logo.jpeg";
import "../../styles/vector-landing-scoped.css";
import { MeetVectorIntegrationsHub } from "./MeetVectorIntegrationsHub.tsx";

const DEMO_CAL_URL = "https://calendar.app.google/GcS9iPFBuL9XFzhc8";

const PERCEPTION_CAPABILITIES = [
  {
    title: "Beyond what your tools log",
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

const ACTION_CAPABILITIES = [
  {
    title: "Surfaces what's actually broken",
    sub: "Highlights real execution gaps (not noise, not reports).",
  },
  {
    title: "Tells you what to do next",
    sub: "Every issue comes with a concrete action: assign, clarify, link, or escalate.",
  },
  {
    title: "Handles coordination for you",
    sub: "Follows up, nudges, connects people, and closes loops automatically.",
  },
  {
    title: "Escalates only when needed",
    sub: "You step in for decisions. Vector handles the rest.",
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
        Vector gives you visibility into how work flows across your team, where things are progressing, where they are
        stuck, and who might need support. Not to rank or score individuals, but to help you act before small blockers
        become big problems. Your team stays focused. You stay informed.
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
    copy: "of coding time unlocked when context is available. Engineers stay in flow instead of rebuilding what they already knew.",
  },
  {
    accent: false,
    stat: "4.4h",
    copy: "saved per senior engineer per week. When context is available, decisions are made faster.",
  },
  {
    accent: true,
    stat: "3.2x",
    copy: "less technical debt when agents work with full context. Every session starts informed, not from zero.",
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
            marginBottom: "0px",
            padding: "16px",
            border: "1px solid #F0F0F0",
            borderRadius: "10px",
            background: "#FAFAFA",
            fontSize: "11px",
            flex: "1",
            height: "180px",
            minHeight: "180px",
            maxHeight: "180px",
            overflow: "hidden",
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
              PR #847 approved
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
              ENG-203 blocked
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
              <span style={{ color: "#E878BE" }}>@marie</span>
              {" "}retry logic is a mess, let's cap at 3 attempts across all services
            </div>
          </div>
        </div>
      ),
    },
    {
      visual: (
        <div
          style={{
            marginBottom: "0px",
            padding: "16px",
            border: "1px solid #F0F0F0",
            borderRadius: "10px",
            background: "#FAFAFA",
            fontSize: "11px",
            flex: "1",
            height: "180px",
            minHeight: "180px",
            maxHeight: "180px",
            overflow: "hidden",
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
            <span>
              When did we decide to move to a monorepo?
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
            </span>
          </div>
          <div
            style={{
              background: "#FFF0F8",
              border: "1px solid #FFB3D9",
              borderRadius: "6px",
              padding: "8px 10px",
              color: "#333",
              lineHeight: 1.5,
              fontSize: "11px",
            }}
          >
            Decided during an engineering call in{" "}
            <span style={{ color: "#E878BE" }}>#backend-arch</span>, February 2026, effective on GitHub in March 2026. @alex, @thomas and @marie aligned.
          </div>
        </div>
      ),
    },
    {
      visual: (
        <div
          style={{
            marginBottom: "0px",
            padding: "16px",
            border: "1px solid #F0F0F0",
            borderRadius: "10px",
            background: "#FAFAFA",
            height: "180px",
            minHeight: "180px",
            maxHeight: "180px",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            flex: "1",
          }}
        >
          <svg viewBox="0 0 300 80" width="100%" height="70" preserveAspectRatio="none">
            <defs>
              <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#E878BE" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#E878BE" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0,75 C50,73 100,65 140,45 C180,25 220,10 300,2"
              fill="none"
              stroke="#E878BE"
              strokeWidth="2"
            />
            <path
              d="M0,75 C50,73 100,65 140,45 C180,25 220,10 300,2 L300,80 L0,80 Z"
              fill="url(#curveGrad)"
            />
            <circle cx="0" cy="75" r="3" fill="#E878BE" opacity="0.4" />
            <circle cx="140" cy="45" r="3" fill="#E878BE" opacity="0.7" />
            <circle cx="300" cy="2" r="3" fill="#E878BE" />
          </svg>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              paddingTop: "4px",
            }}
          >
            {[
              { label: "Day 1", sub: "Stack connected" },
              { label: "Week 1", sub: "Patterns identified" },
              { label: "Week 3", sub: "Deep execution context" },
            ].map((point) => (
              <div
                key={point.label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "2px",
                }}
              >
                <div
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    color: "#333",
                  }}
                >
                  {point.label}
                </div>
                <div
                  style={{
                    fontSize: "10px",
                    color: "#AAAAAA",
                    textAlign: "center",
                  }}
                >
                  {point.sub}
                </div>
              </div>
            ))}
          </div>
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
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            gap: "8px",
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
              marginTop: "0",
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

function ValuePillarCapabilityList({ items }: { items: readonly { title: string; sub: string }[] }) {
  return (
    <ul className="empowers-nav empower-cap-list" aria-label="Capabilities">
      {items.map((item) => (
        <li key={item.title} className="empower-cap-item">
          <span className="empower-nav-title">{item.title}</span>
          <span className="empower-nav-sub">{item.sub}</span>
        </li>
      ))}
    </ul>
  );
}

function HeroSlackVectorAppIcon() {
  return (
    <div className="hero-slack-app-icon" aria-hidden="true">
      <img className="hero-slack-app-icon__img" src={vectorHeroAvatarUrl} alt="" />
    </div>
  );
}

/** Slack-style insight for the “moves work forward” pillar (hero-adjacent visual language). */
function MovesWorkForwardSlackPreview() {
  return (
    <div
      className="empower-action-slack"
      role="region"
      aria-label="Example: Vector posts a coordination gap with evidence and suggested next steps in Slack"
    >
      <div className="hero-slack-mock">
        <div className="hero-slack-mock__topbar">
          <span className="hero-slack-mock__hash" aria-hidden="true">
            #
          </span>
          <span className="hero-slack-mock__channel">product</span>
        </div>
        <div className="hero-slack-mock__thread hero-slack-mock__thread--single">
          <article className="hero-slack-msg" aria-label="Coordination gap: agreement never became a ticket">
            <div className="hero-slack-msg__head">
              <HeroSlackVectorAppIcon />
              <div className="hero-slack-msg__meta">
                <span className="hero-slack-msg__app">Vector</span>
                <span className="hero-slack-msg__time">5:55 PM</span>
              </div>
            </div>
            <div className="hero-slack-msg__body">
              <p className="hero-slack-msg__title">
                <span className="hero-slack-msg__badge">Coordination gap</span>
                <span className="hero-slack-msg__dash">: </span>
                <span>agreement never became a ticket</span>
              </p>
              <p className="hero-slack-msg__summary">
                <span className="hero-slack-mention">@Alex</span> and{" "}
                <span className="hero-slack-mention hero-slack-mention--alt">@Sam</span> joined the design review;
                everyone aligned on shipping <strong>the analytics cut this week</strong>, but{" "}
                <strong>no Linear issue</strong> was filed and <strong>no owner</strong> was set.
              </p>
              <p className="hero-slack-msg__label">Evidence</p>
              <ul className="hero-slack-msg__list">
                <li>
                  <strong>Slack</strong>: thread ends with “will track in Linear” · <strong>no link posted</strong>
                </li>
                <li>
                  <strong>Linear</strong>: <strong>0 issues</strong> tied to that decision ·{" "}
                  <strong>no assignment</strong> to <span className="hero-slack-mention">@Alex</span>
                </li>
                <li>
                  <strong>GitHub</strong>: draft PR open <strong>4 days</strong> · still <strong>unassigned</strong>
                </li>
              </ul>
              <p className="hero-slack-msg__label">
                Suggested action <span aria-hidden="true">💡</span>
              </p>
              <p className="hero-slack-msg__action">
                👉 Open a Linear issue for the <strong>analytics cut</strong>, assign{" "}
                <span className="hero-slack-mention">@Alex</span>, and paste the link in{" "}
                <strong>#product</strong>.
              </p>
              <div className="hero-slack-msg__ctas" aria-hidden="true">
                <span className="hero-slack-cta hero-slack-cta--primary">Execute</span>
                <span className="hero-slack-cta hero-slack-cta--secondary">{"I'll handle it myself"}</span>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  );
}

function LandingHeroSlackPreview() {
  return (
    <div
      className="hero-slack-mock"
      role="region"
      aria-label="Slack preview: Vector posts execution risks with evidence and suggested actions in channel"
    >
      <div className="hero-slack-mock__topbar">
        <span className="hero-slack-mock__hash" aria-hidden="true">
          #
        </span>
        <span className="hero-slack-mock__channel">management</span>
      </div>
      <div className="hero-slack-mock__thread">
        <article className="hero-slack-msg" aria-label="Execution gap: decision not tracked">
          <div className="hero-slack-msg__head">
            <HeroSlackVectorAppIcon />
            <div className="hero-slack-msg__meta">
              <span className="hero-slack-msg__app">Vector</span>
              <span className="hero-slack-msg__time">10:14 AM</span>
            </div>
          </div>
          <div className="hero-slack-msg__body">
            <p className="hero-slack-msg__title">
              <span className="hero-slack-msg__badge">Execution gap</span>
              <span className="hero-slack-msg__dash">: </span>
              <span>decision not tracked</span>
            </p>
            <p className="hero-slack-msg__summary">
              The team aligned on a payment retry fix on the call, but nothing was filed in Linear.
            </p>
            <p className="hero-slack-msg__label">Evidence</p>
            <ul className="hero-slack-msg__list">
              <li>
                <strong>Slack</strong>: recap notes “no ticket filed.”
              </li>
              <li>
                <strong>Linear</strong>: 0 issues linked to that call.
              </li>
              <li>
                <strong>#payments</strong>: summary posted, no linked issue.
              </li>
            </ul>
            <p className="hero-slack-msg__label">
              Suggested action <span aria-hidden="true">💡</span>
            </p>
            <p className="hero-slack-msg__action">👉 Open a Linear issue, assign an owner, paste the link in #payments.</p>
            <div className="hero-slack-msg__ctas" aria-hidden="true">
              <span className="hero-slack-cta hero-slack-cta--primary">Execute</span>
              <span className="hero-slack-cta hero-slack-cta--secondary">I&apos;ll handle it myself</span>
            </div>
          </div>
        </article>

        <article className="hero-slack-msg" aria-label="Execution block: cross-team dependency">
          <div className="hero-slack-msg__head">
            <HeroSlackVectorAppIcon />
            <div className="hero-slack-msg__meta">
              <span className="hero-slack-msg__app">Vector</span>
              <span className="hero-slack-msg__time">3:48 PM</span>
            </div>
          </div>
          <div className="hero-slack-msg__body">
            <p className="hero-slack-msg__title">
              <span className="hero-slack-msg__badge hero-slack-msg__badge--block">Execution block</span>
              <span className="hero-slack-msg__dash">: </span>
              <span>cross-team dependency stuck</span>
            </p>
            <p className="hero-slack-msg__summary">
              An API refactor is blocked on Infra approval, and there has been no reply in #infra-asks.
            </p>
            <p className="hero-slack-msg__label">Evidence</p>
            <ul className="hero-slack-msg__list">
              <li>
                <strong>Slack</strong>: ping in #infra-asks 2 days ago, no reply.
              </li>
              <li>
                <strong>GitHub</strong>: PR #512 blocked until approval lands.
              </li>
              <li>
                <strong>Linear</strong>: PAY-640 blocked on review, no named reviewer.
              </li>
            </ul>
            <p className="hero-slack-msg__label">
              Suggested action <span aria-hidden="true">💡</span>
            </p>
            <p className="hero-slack-msg__action">
              👉 Escalate with a named owner in #infra-asks and pin an unblock date.
            </p>
            <div className="hero-slack-msg__ctas" aria-hidden="true">
              <span className="hero-slack-cta hero-slack-cta--primary">Escalate in #infra-asks</span>
              <span className="hero-slack-cta hero-slack-cta--secondary">I&apos;ll handle it myself</span>
            </div>
          </div>
        </article>
      </div>
    </div>
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

function AnimatedStatBlock({
  block,
}: {
  block: { stat: string; copy: string; accent: boolean };
}) {
  const colRef = useRevealInViewRef();
  const [displayed, setDisplayed] = React.useState("0");
  const [animated, setAnimated] = React.useState(false);

  React.useEffect(() => {
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
    <article ref={colRef as React.RefObject<HTMLElement>} className="impact-strip__col">
      <p className={`impact-strip__stat${block.accent ? " impact-strip__stat--accent" : ""}`}>
        {animated ? displayed : "0"}
      </p>
      <p className="impact-strip__copy">{block.copy}</p>
    </article>
  );
}

function HeroGraphBackground() {
  const svgRef = React.useRef<SVGSVGElement>(null);
  const [mouse, setMouse] = React.useState({
    x: -999,
    y: -999,
  });

  const baseNodes = [
    { cx: 80, cy: 60, r: 2 },
    { cx: 160, cy: 120, r: 3 },
    { cx: 240, cy: 50, r: 2 },
    { cx: 320, cy: 150, r: 4 },
    { cx: 420, cy: 80, r: 2 },
    { cx: 500, cy: 180, r: 3 },
    { cx: 580, cy: 60, r: 2 },
    { cx: 660, cy: 140, r: 4 },
    { cx: 740, cy: 80, r: 2 },
    { cx: 120, cy: 220, r: 3 },
    { cx: 200, cy: 300, r: 2 },
    { cx: 300, cy: 250, r: 4 },
    { cx: 380, cy: 320, r: 2 },
    { cx: 460, cy: 260, r: 3 },
    { cx: 540, cy: 340, r: 2 },
    { cx: 620, cy: 240, r: 4 },
    { cx: 700, cy: 320, r: 2 },
    { cx: 760, cy: 200, r: 3 },
    { cx: 60, cy: 340, r: 2 },
    { cx: 180, cy: 380, r: 2 },
    { cx: 350, cy: 380, r: 3 },
    { cx: 480, cy: 360, r: 2 },
    { cx: 600, cy: 380, r: 2 },
    { cx: 720, cy: 360, r: 3 },
    { cx: 780, cy: 300, r: 2 },
    { cx: 260, cy: 180, r: 3 },
    { cx: 440, cy: 200, r: 2 },
    { cx: 560, cy: 140, r: 3 },
    { cx: 680, cy: 280, r: 2 },
    { cx: 140, cy: 160, r: 4 },
    { cx: 400, cy: 40, r: 2 },
    { cx: 520, cy: 280, r: 3 },
    { cx: 100, cy: 380, r: 2 },
    { cx: 280, cy: 80, r: 2 },
    { cx: 640, cy: 40, r: 2 },
    { cx: 760, cy: 140, r: 3 },
    { cx: 220, cy: 200, r: 2 },
    { cx: 360, cy: 260, r: 2 },
    { cx: 500, cy: 80, r: 2 },
    { cx: 680, cy: 380, r: 2 },
    { cx: 40, cy: 180, r: 2 },
    { cx: 340, cy: 40, r: 2 },
    { cx: 600, cy: 300, r: 2 },
    { cx: 160, cy: 280, r: 2 },
    { cx: 460, cy: 140, r: 3 },
    { cx: 740, cy: 240, r: 2 },
    { cx: 280, cy: 340, r: 2 },
    { cx: 540, cy: 220, r: 2 },
    { cx: 80, cy: 280, r: 2 },
    { cx: 420, cy: 300, r: 2 },
  ];

  const edges = [
    [0, 1], [1, 2], [1, 3], [2, 4], [3, 4], [3, 5],
    [4, 6], [5, 6], [5, 7], [6, 8], [7, 8], [0, 9],
    [9, 10], [10, 11], [11, 12], [11, 13], [12, 13],
    [13, 14], [14, 15], [15, 16], [15, 17], [16, 17],
    [9, 18], [18, 19], [19, 20], [20, 21], [21, 22],
    [22, 23], [23, 24], [25, 1], [25, 3], [26, 5],
    [26, 13], [27, 7], [27, 15], [28, 17], [28, 16],
    [29, 1], [29, 9], [3, 25], [5, 26], [7, 27],
    [30, 4], [30, 6], [31, 5], [31, 13], [32, 18],
    [32, 10], [33, 1], [33, 25], [34, 6], [34, 27],
    [35, 8], [35, 17], [36, 25], [36, 11], [37, 11],
    [37, 13], [38, 4], [38, 30], [39, 16], [39, 28],
    [40, 9], [40, 0], [41, 30], [41, 33], [42, 15],
    [42, 31], [43, 10], [43, 36], [44, 26], [44, 38],
    [45, 35], [45, 17], [46, 11], [46, 37], [47, 26],
    [47, 31], [48, 0], [48, 40], [49, 13], [49, 37],
    [1, 29], [3, 36], [5, 44], [7, 45], [11, 46],
    [13, 49], [15, 42], [25, 33], [27, 34], [29, 43],
    [30, 41], [31, 47], [36, 43], [38, 44], [40, 48],
  ];

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMouse({
      x: (e.clientX - rect.left) * (800 / rect.width),
      y: (e.clientY - rect.top) * (400 / rect.height),
    });
  };

  const handleMouseLeave = () => {
    setMouse({ x: -999, y: -999 });
  };

  const nodes = baseNodes.map((node) => {
    const dx = mouse.x - node.cx;
    const dy = mouse.y - node.cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const maxDist = 120;
    const force = Math.max(0, (maxDist - dist) / maxDist);
    const angle = Math.atan2(dy, dx);
    const push = force * 40;
    return {
      ...node,
      cx: node.cx - Math.cos(angle) * push,
      cy: node.cy - Math.sin(angle) * push,
    };
  });

  return (
    <div className="hero-graph" aria-hidden="true">
      <svg
        ref={svgRef}
        viewBox="0 0 800 400"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid slice"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {edges.map(([a, b], i) => (
          <line
            key={i}
            x1={nodes[a].cx}
            y1={nodes[a].cy}
            x2={nodes[b].cx}
            y2={nodes[b].cy}
            stroke="#E878BE"
            strokeWidth="0.8"
            opacity="0.2"
          />
        ))}
        {nodes.map((node, i) => (
          <circle
            key={i}
            cx={node.cx}
            cy={node.cy}
            r={node.r}
            fill="#E878BE"
            opacity="0.6"
          />
        ))}
      </svg>
    </div>
  );
}

function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(
    () => window.innerWidth <= 767
  );
  React.useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= 767);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return isMobile;
}

export function VectorLandingBody({ signedInWorkspaceCta }: VectorLandingBodyProps) {
  const isMobile = useIsMobile();

  return (
    <div id="vector-landing">
      <div className="page-bg" aria-hidden="true">
        <div className="page-bg__solid" />
        <div className="page-bg__grid" />
      </div>

      <main>
        <div className="wrap hero hero--centered">
          <HeroGraphBackground />
          <div className="hero-centered-shell">
            <div className="hero-copy hero-copy--centered">
              <h1>
                <span className="hero-headline-line">
                  Agents don&apos;t inherit context. <span className="accent">Vector does.</span>
                </span>
              </h1>
              <p className="sub hero-sub hero-sub--centered">
                Vector builds a persistent understanding of how your teams ship, queryable by humans and agents alike.
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
                  Vector is a living execution graph of your org, extracting hidden insights from structured data and human signals across your entire stack. Queryable by your team, and legible by every agent in it.
                </p>
              </div>
              <MeetVectorIntegrationsHub />
            </div>
          </div>
        </section>

        <section className="join-strip" id="join-strip" aria-labelledby="join-strip-heading">
          <div className="join-strip__inner">
            <h2 id="join-strip-heading" className="join-strip__heading">
              Unlock your <span className="accent">org's intelligence.</span>
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
                <AnimatedStatBlock key={block.stat} block={block} />
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
              className="security-grid"
              style={{
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
                  title: "Built with clear boundaries",
                  body: "Vector reads public channels and work tools. Private messages, customer data, and HR records are never in scope.",
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
                  title: "AWS. Encrypted end to end.",
                  body: "AES-256 at rest, TLS 1.2+ in transit. GDPR compliant. SOC 2 in progress.",
                },
              ].map((block, index) => (
                <div
                  key={block.title}
                  style={{
                    border: "1px solid #E8E8E8",
                    borderRadius: "12px",
                    padding: "28px 32px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    ...(index === 2 ? { gridColumn: "1", padding: "20px 24px" } : {}),
                    ...(index === 3 ? { gridColumn: "2" } : {}),
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

      <footer
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "12px",
          padding: "24px 0",
        }}
      >
        <p>© {new Date().getFullYear()} Vector</p>
        <a
          href="https://www.linkedin.com/company/myvector-ai/"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Vector on LinkedIn"
          style={{ color: "#AAAAAA", display: "inline-flex" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
        </a>
      </footer>
    </div>
  );
}
