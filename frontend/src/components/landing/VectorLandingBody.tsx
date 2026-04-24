import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import heroOrgMichelleUrl from "../../assets/hero-org-michelle.png";
import vectorHeroAvatarUrl from "../../assets/vector-white-bg.png";
import "../../styles/vector-landing-scoped.css";
import { MeetVectorIntegrationsHub } from "./MeetVectorIntegrationsHub.tsx";

const DEMO_CAL_URL = "https://calendar.app.google/GcS9iPFBuL9XFzhc8";

const HERO_CHAT_DELAYS_MS = [420, 580, 560, 1350, 920] as const;
const HERO_CHAT_STEP_COUNT = 6;

type EmpowerKey = "visibility" | "drift" | "handling" | "escalation";

const EMPOWER_META: Record<
  EmpowerKey,
  { tabId: string; title: string; sub: string; bubbles: string[]; ariaLabel: string; time: string }
> = {
  visibility: {
    tabId: "empower-tab-visibility",
    title: "Execution visibility",
    sub: "Instantly know what matters",
    ariaLabel: "Execution visibility example in Slack",
    time: "8:02 AM",
    bubbles: [
      "Morning Alex, quick overview ✨",
      "<strong>Checkout:</strong><br />• PR waiting on review since yesterday<br />• Auth migration is unblocked and moving",
      "I nudged for a reviewer and aligned ownership.",
      "Everything else is on track.",
    ],
  },
  drift: {
    tabId: "empower-tab-drift",
    title: "Drift detection",
    sub: "Catch issues before they slow you down",
    ariaLabel: "Drift detection example in Slack",
    time: "3:14 PM",
    bubbles: [
      "Heads up: small drift detected.",
      "The auth service PR has been inactive for ~1 day and no reviewer is clearly assigned.",
      "I'm resolving it now before it blocks anything.",
    ],
  },
  handling: {
    tabId: "empower-tab-handling",
    title: "Execution handling",
    sub: "Vector moves work forward for you",
    ariaLabel: "Execution handling example in Slack",
    time: "11:08 AM",
    bubbles: [
      "I handled this in <strong>#eng-shipping</strong> so you don't have to.",
      "→ Assigned Sam as reviewer<br />→ Clarified ownership in Linear<br />→ Scheduled a follow-up if no activity",
      "I'll keep things moving and update you if needed.",
    ],
  },
  escalation: {
    tabId: "empower-tab-escalation",
    title: "Smart escalation",
    sub: "Vector only involves you when a decision is needed",
    ariaLabel: "Smart escalation example in Slack",
    time: "4:47 PM",
    bubbles: [
      "One item needs your input.",
      "Checkout launch scope and timeline don't align.",
      "Options:<br />• Move the release date<br />• Reduce scope for this cycle",
      "Tell me what you prefer, and I'll handle the rest.",
    ],
  },
};

function EmpowerPanel({ feature }: { feature: EmpowerKey }) {
  const meta = EMPOWER_META[feature];
  return (
    <div className="chat-card" role="region" aria-label={meta.ariaLabel}>
      <div className="chat-shell">
        <div className="chat-thread">
          <div className="chat-block chat-row">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>{meta.time}</span>
              </div>
              {meta.bubbles.map((html, i) => (
                <div key={i} className="bubble" dangerouslySetInnerHTML={{ __html: html }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function useHeroChatReveal() {
  const [visibleSteps, setVisibleSteps] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    const prefersReduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduce) {
      setVisibleSteps(new Set([0, 1, 2, 3, 4, 5]));
      return;
    }
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    let t = 0;
    for (let i = 0; i < HERO_CHAT_STEP_COUNT; i++) {
      const step = i;
      timeouts.push(
        setTimeout(() => {
          setVisibleSteps((prev) => new Set(prev).add(step));
        }, t),
      );
      if (i < HERO_CHAT_DELAYS_MS.length) t += HERO_CHAT_DELAYS_MS[i]!;
    }
    return () => timeouts.forEach(clearTimeout);
  }, []);

  return visibleSteps;
}

function useProblemBannerInView() {
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

export function VectorLandingBody({ signedInWorkspaceCta }: VectorLandingBodyProps) {
  const visibleSteps = useHeroChatReveal();
  const problemBannerRef = useProblemBannerInView();
  const [empower, setEmpower] = useState<EmpowerKey>("visibility");

  const stepClass = (n: number) => (visibleSteps.has(n) ? "is-visible" : "");

  return (
    <div id="vector-landing">
      <div className="page-bg" aria-hidden="true">
        <div className="page-bg__solid" />
        <div className="page-bg__grid" />
      </div>

      <main>
        <div className="wrap hero">
          <div className="hero-shell">
            <div className="hero-copy">
              <div className="hero-lead">
                <h1>
                  <span className="block hero-headline-line">Turn messy execution into</span>
                  <span className="block hero-headline-line">
                    <span className="accent">predictable delivery.</span>
                  </span>
                </h1>
              </div>
              <div className="hero-sub-row">
                <p className="sub hero-sub">
                  <strong>Vector handles execution behind the scenes, so you don’t have to.</strong>
                </p>
                <div className="hero-cta-row">
                  <a className="btn-light" href={DEMO_CAL_URL} target="_blank" rel="noopener noreferrer">
                    Book a demo
                  </a>
                </div>
              </div>
            </div>
            <div className="hero-product">
              <div className="hero-product__chat-wrap">
                <div className="chat-card">
                  <div className="chat-shell">
                    <div className="chat-head">
                      <strong># checkout</strong>
                      <span className="muted">·</span>
                      <span className="muted">Engineering</span>
                    </div>
                    <div className="chat-thread">
                      <div className={`chat-block chat-row ${stepClass(0)}`} data-seq={0}>
                        <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                            <span style={{ fontSize: 13, color: "#a1a1aa" }}>9:41 AM</span>
                          </div>
                          <div className="bubble">Hey, quick heads up.</div>
                        </div>
                      </div>
                      <div className={`chat-block chat-row ${stepClass(1)}`} data-seq={1}>
                        <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                            <span style={{ fontSize: 13, color: "#a1a1aa" }}>9:41 AM</span>
                          </div>
                          <div className="bubble">
                            The auth PR is still in review. I’ve aligned with Sam to pick it up this morning 🤓
                          </div>
                        </div>
                      </div>
                      <div className={`chat-block chat-row--alex ${stepClass(2)}`} data-seq={2}>
                        <div className="bubble-meta bubble-meta--alex">
                          <img className="avatar" src={heroOrgMichelleUrl} alt="" />
                          <span style={{ fontSize: 14, fontWeight: 600 }}>Alex</span>
                          <span style={{ fontSize: 13, color: "#a1a1aa" }}>9:42 AM</span>
                        </div>
                        <div className="bubble bubble--alex">Got it. Any risk for checkout?</div>
                      </div>
                      <div className={`chat-block chat-row ${stepClass(3)}`} data-seq={3}>
                        <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                            <span style={{ fontSize: 13, color: "#a1a1aa" }}>9:41 AM</span>
                          </div>
                          <div className="bubble">All good.</div>
                          <div className="bubble">
                            I pushed for a quick review and adjusted scope slightly so checkout can ship today without
                            delay.
                          </div>
                          <div className="bubble">Full version lands tomorrow.</div>
                        </div>
                      </div>
                      <div className={`chat-block chat-row--alex ${stepClass(4)}`} data-seq={4}>
                        <div className="bubble-meta bubble-meta--alex">
                          <img className="avatar" src={heroOrgMichelleUrl} alt="" />
                          <span style={{ fontSize: 14, fontWeight: 600 }}>Alex</span>
                          <span style={{ fontSize: 13, color: "#a1a1aa" }}>9:42 AM</span>
                        </div>
                        <div className="bubble bubble--alex">Perfect 👍</div>
                      </div>
                      <div className={`chat-typing ${stepClass(5)}`} data-seq={5}>
                        <span>Vector is typing</span>
                        <span className="typing-dots" aria-hidden="true">
                          <span />
                          <span />
                          <span />
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <section ref={problemBannerRef} className="problem-banner" aria-label="Execution challenge">
          <div className="problem-banner__grid" aria-hidden="true" />
          <div className="problem-banner__inner">
            <div className="problem-banner__block problem-banner__block--focus">
              <p className="problem-banner__text">Everything looks in progress, but nothing is moving...</p>
            </div>
          </div>
        </section>

        <section className="section" id="meet-vector" aria-labelledby="meet-vector-heading">
          <div className="container">
            <div className="meet-vector-layout">
              <div className="meet-vector-copy">
                <h2 id="meet-vector-heading">
                  Meet <span className="accent">Vector</span>
                </h2>
                <p className="sub meet-vector__sub">Your AI Junior manager</p>
                <p className="sub meet-vector__support">
                  Vector integrates directly into your tools and workflows to give you a clear, real-time understanding of
                  your team’s execution and the insights to improve it.
                </p>
              </div>
              <MeetVectorIntegrationsHub />
            </div>
          </div>
        </section>

        <section className="join-strip" id="join-strip" aria-labelledby="join-strip-heading">
          <div className="join-strip__inner">
            <h2 id="join-strip-heading" className="join-strip__heading">
              Onboard Vector instantly and <span className="accent">improve your execution.</span>
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

        <section className="section" id="core-features">
          <div className="section-inner">
            <header className="text-center">
              <h2>
                How <span className="accent">Vector</span> shows up for you
              </h2>
            </header>
            <div className="empowers-split">
              <div className="empowers-nav" role="tablist" aria-label="Vector capabilities">
                {(Object.keys(EMPOWER_META) as EmpowerKey[]).map((key) => {
                  const m = EMPOWER_META[key];
                  const selected = empower === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      className={`empower-nav-item${selected ? " is-selected" : ""}`}
                      role="tab"
                      id={m.tabId}
                      aria-selected={selected}
                      aria-controls="empower-panel"
                      data-feature={key}
                      onClick={() => setEmpower(key)}
                    >
                      <span className="empower-nav-title">{m.title}</span>
                      <span className="empower-nav-sub">{m.sub}</span>
                    </button>
                  );
                })}
              </div>
              <div
                className="empowers-panel-wrap"
                role="tabpanel"
                id="empower-panel"
                aria-labelledby={EMPOWER_META[empower].tabId}
              >
                <div id="empower-detail-content" className="empower-detail">
                  <EmpowerPanel feature={empower} />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="impact-strip" id="impact" aria-label="What Vector changes for managers">
          <div className="impact-strip__inner">
            <div className="impact-strip__row">
              <article className="impact-strip__col">
                <p className="impact-strip__stat impact-strip__stat--accent">30%</p>
                <p className="impact-strip__copy">
                  Of your week back—spent leading, not chasing status.
                </p>
              </article>
              <article className="impact-strip__col">
                <p className="impact-strip__stat">100%</p>
                <p className="impact-strip__copy">
                  Automated reporting. No more digging into dashboards.
                </p>
              </article>
              <article className="impact-strip__col">
                <p className="impact-strip__stat impact-strip__stat--accent">Always-on</p>
                <p className="impact-strip__copy">
                  Project radar—blind spots surface before they cost you.
                </p>
              </article>
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
                  <span className="cta-step-copy">Connect Vector</span>
                </li>
                <li>
                  <span className="cta-num">2</span>
                  <span className="cta-step-copy">Vector understands how your teams operates</span>
                </li>
                <li>
                  <span className="cta-num">3</span>
                  <span className="cta-step-copy">Vector is ready to work</span>
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
      </main>

      <footer>
        <p>© {new Date().getFullYear()} Vector</p>
      </footer>
    </div>
  );
}
