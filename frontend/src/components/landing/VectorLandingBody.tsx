import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import heroOrgMichelleUrl from "../../assets/hero-org-michelle.png";
import vectorHeroAvatarUrl from "../../assets/vector-white-bg.png";
import "../../styles/vector-landing-scoped.css";
import { MeetVectorIntegrationsHub } from "./MeetVectorIntegrationsHub.tsx";

const DEMO_CAL_URL = "https://calendar.app.google/GcS9iPFBuL9XFzhc8";

const HERO_CHAT_DELAYS_MS = [420, 580, 560, 1350, 920] as const;
const HERO_CHAT_STEP_COUNT = 6;

const PERCEPTION_CAPABILITIES = [
  {
    title: "Understands real work",
    sub: "Pulls signals from GitHub, Linear, Slack, and docs, including what people say, not just what they log.",
  },
  {
    title: "Captures human signals",
    sub: "Detects commitments, blockers, ownership gaps, and ambiguity, even when implicit.",
  },
  {
    title: "Reconstructs execution state",
    sub: "Knows what's moving, stuck, unclear, or drifting across threads and tools.",
  },
  {
    title: "Connects everything together",
    sub: "Automatically links discussions to execution and outcomes. No manual stitching.",
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

const IMPACT_BLOCKS = [
  {
    accent: true,
    stat: "30%",
    copy: "Of your week back for leading, not stitching updates across tools.",
  },
  {
    accent: false,
    stat: "Runs for you",
    copy: "Follow-ups, owners, and links keep moving so work doesn't die in the thread.",
  },
  {
    accent: true,
    stat: "Always-on",
    copy: "Stalls and gaps surface while you can still change the outcome.",
  },
] as const;

function ValuePillarCapabilityGrid({ items }: { items: readonly { title: string; sub: string }[] }) {
  return (
    <ul className="empower-cap-list empower-cap-list--grid" aria-label="Capabilities">
      {items.map((item) => (
        <li key={item.title} className="empower-cap-item">
          <span className="empower-nav-title">{item.title}</span>
          <span className="empower-nav-sub">{item.sub}</span>
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

function ActionProductPreview() {
  return (
    <div
      className="chat-card chat-card--compact"
      role="region"
      aria-label="Vector detects stalled checkout work, assigns Alex, links PR, and follows up"
    >
      <div className="chat-shell">
        <div className="chat-head">
          <strong>Checkout</strong>
          <span className="muted">·</span>
          <span className="muted">Coordination</span>
        </div>
        <div className="chat-thread">
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:08 PM</span>
              </div>
              <div className="bubble">
                Checkout ticket has been in progress for 7 days with no updates. Likely stalled.
              </div>
            </div>
          </div>
          <div className="chat-block chat-row--alex is-visible">
            <div className="bubble-meta bubble-meta--alex">
              <img className="avatar" src={heroOrgMichelleUrl} alt="" />
              <span style={{ fontSize: 14, fontWeight: 600 }}>Manager</span>
              <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:09 PM</span>
            </div>
            <div className="bubble bubble--alex">Yeah</div>
          </div>
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:09 PM</span>
              </div>
              <div className="bubble">
                Assigning to Alex and linking related PR. I&apos;ll follow up if no progress in 24h.
              </div>
            </div>
          </div>
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:09 PM</span>
              </div>
              <div className="bubble">Done. I&apos;ll keep an eye on it.</div>
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

export function VectorLandingBody({ signedInWorkspaceCta }: VectorLandingBodyProps) {
  const visibleSteps = useHeroChatReveal();
  const problemBannerRef = useRevealInViewRef();

  const timelineSlots = [
    {
      time: "9:00",
      without:
        "You prep your team's weekly call, gathering data from tickets, PRs, messages, hoping nothing important is missing.",
      with: "Vector briefs the call: shipped, stuck, risks. → You lead, not chase for updates.",
    },
    {
      time: "10:15",
      without:
        "Rebecca's PR is not merged for days, you ping her and discover it's stuck in an endless review loop.",
      with: "2h of strategic work. No interruptions.",
    },
    {
      time: "2:30",
      without:
        "You just discovered an insane thread with 78 exchanges, it'll take a while to catch up and sort this out.",
      with: "Escalation with context + next action. Issue unblocked fast.",
    },
    {
      time: "4:40",
      without:
        "Your boss is asking for more visibility on your team and projects so you start writing a detailed report.",
      with: "Report ready. You review, not write.",
    },
  ] as const;

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
                  <strong>Vector surfaces risks and guides your next steps based on live data from your team.</strong>
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
                <p className="sub meet-vector__sub">Your new AI team member</p>
                <p className="sub meet-vector__support">
                  Vector integrates with the tools your team already uses, giving you a real-time view of your
                  team’s execution. He spots risks early, highlights where progress is slowing down, and helps you
                  see what needs attention next.
                </p>
                <p className="sub meet-vector__support">
                  Instead of chasing updates across different sources and stakeholders, Vector brings everything
                  together so you can focus on delivery.
                </p>
              </div>
              <MeetVectorIntegrationsHub />
            </div>
          </div>
        </section>

        <section className="join-strip" id="join-strip" aria-labelledby="join-strip-heading">
          <div className="join-strip__inner">
            <h2 id="join-strip-heading" className="join-strip__heading">
              Onboard Vector and <span className="accent">improve your execution.</span>
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
                    Vector <span className="accent">sees</span> what your team is really doing
                  </h2>
                </header>
                <div className="value-pillar-features">
                  <ValuePillarCapabilityGrid items={PERCEPTION_CAPABILITIES} />
                </div>
              </div>
            </div>
          </section>

          <section className="section" aria-labelledby="value-pillar-action-heading">
            <div className="section-inner value-pillars">
              <div className="value-pillar">
                <header className="value-pillar__header text-center">
                  <h2 id="value-pillar-action-heading">
                    Vector <span className="accent">moves work forward</span> for you
                  </h2>
                </header>
                <div className="empowers-split">
                  <ValuePillarCapabilityList items={ACTION_CAPABILITIES} />
                  <div className="empowers-panel-wrap">
                    <div className="empower-detail">
                      <ActionProductPreview />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section className="impact-strip" id="impact" aria-label="What changes when Vector runs coordination">
          <div className="impact-strip__inner">
            <div className="impact-strip__row">
              {IMPACT_BLOCKS.map((block) => (
                <article key={block.stat} className="impact-strip__col">
                  <p className={`impact-strip__stat${block.accent ? " impact-strip__stat--accent" : ""}`}>
                    {block.stat}
                  </p>
                  <p className="impact-strip__copy">{block.copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="timeline-contrast" aria-labelledby="timeline-contrast-heading">
          <div className="timeline-contrast__inner">
            <header className="timeline-contrast__header">
              <h2 id="timeline-contrast-heading">One timeline. Two realities.</h2>
            </header>
            <div className="timeline-contrast__sync" aria-label="Execution timeline comparison">
              <div className="timeline-contrast__labels">
                <p className="timeline-contrast__label timeline-contrast__label--without">Without Vector</p>
                <p className="timeline-contrast__label timeline-contrast__label--with">With Vector</p>
              </div>

              <div className="timeline-contrast__rows" role="list">
                {timelineSlots.map((slot) => (
                  <div key={slot.time} className="timeline-contrast__slot" role="listitem">
                    <div className="timeline-contrast__side timeline-contrast__side--without">
                      <span className="timeline-contrast__track" aria-hidden="true" />
                      <span className="timeline-contrast__dot" aria-hidden="true" />
                      <p className="timeline-contrast__text">
                        {slot.time}. {slot.without}
                      </p>
                    </div>
                    <div className="timeline-contrast__side timeline-contrast__side--with">
                      <span className="timeline-contrast__track" aria-hidden="true" />
                      <span className="timeline-contrast__dot" aria-hidden="true" />
                      <p className="timeline-contrast__text">
                        <span className="timeline-contrast__stamp">{slot.time}.</span> {slot.with}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
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
                  <span className="cta-step-copy">Vector gives you instant insights</span>
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
