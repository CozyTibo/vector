import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import broUrl from "../../assets/bro.png";
import heroOrgMichelleUrl from "../../assets/hero-org-michelle.png";
import loreenUrl from "../../assets/loreen.png";
import vectorHeroAvatarUrl from "../../assets/vector-hero-avatar.png";
import vectorHqUrl from "../../assets/vector-hq.png";
import "../../styles/vector-landing-scoped.css";

const DEMO_CAL_URL = "https://calendar.app.google/1kwPDrjBZxVVaBAL6";

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

function LinearLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden focusable="false">
      <path
        fill="currentColor"
        d="M2.886 4.18A11.982 11.982 0 0 1 11.99 0C18.624 0 24 5.376 24 12.009c0 3.64-1.62 6.903-4.18 9.105L2.887 4.18ZM1.817 5.626l16.556 16.556c-.524.33-1.075.62-1.65.866L.951 7.277c.247-.575.537-1.126.866-1.65ZM.322 9.163l14.515 14.515c-.71.172-1.443.282-2.195.322L0 11.358a12 12 0 0 1 .322-2.195Zm-.17 4.862 9.823 9.824a12.02 12.02 0 0 1-9.824-9.824Z"
      />
    </svg>
  );
}

function GitHubLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden focusable="false">
      <path
        fill="currentColor"
        d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
      />
    </svg>
  );
}

function NotionLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden focusable="false">
      <path
        fill="currentColor"
        d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z"
      />
    </svg>
  );
}

function SlackLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden focusable="false">
      <path
        fill="currentColor"
        d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.528 2.528 0 0 1-2.52-2.521V2.522A2.528 2.528 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.528 2.528 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.528 2.528 0 0 1-2.52-2.523 2.528 2.528 0 0 1 2.52-2.52h6.313A2.528 2.528 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"
      />
    </svg>
  );
}

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

function useMeetVectorSnippetInView() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const snippet = ref.current;
    if (!snippet) return;
    snippet.classList.add("is-animating");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      snippet.classList.add("is-inview");
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setTimeout(() => {
              entry.target.classList.add("is-inview");
            }, 160);
            obs.unobserve(entry.target);
          }
        }
      },
      { root: null, rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );
    obs.observe(snippet);
    return () => obs.disconnect();
  }, []);
  return ref;
}

export function VectorLandingBody() {
  const visibleSteps = useHeroChatReveal();
  const problemBannerRef = useProblemBannerInView();
  const meetSnippetRef = useMeetVectorSnippetInView();
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
                  <span className="block">Chase results,</span>
                  <span className="block">
                    Not <span className="accent">updates.</span>
                  </span>
                </h1>
              </div>
              <div className="hero-sub-row">
                <p className="sub hero-sub">
                  <strong>Vector handles execution behind the scenes, so you don’t have to.</strong>
                </p>
                <div className="hero-cta-row">
                  <a className="btn-pill btn-pill--hero" href="#meet-vector">
                    Meet Vector
                  </a>
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
              <p className="problem-banner__text">Everything looks in progress, but nothing is moving.</p>
              <p className="problem-banner__text">It’s just another day figuring it out.</p>
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
                <p className="sub meet-vector__sub">
                  Your always-on AI teammate who <strong>runs execution with you.</strong>
                </p>
                <p className="sub meet-vector__support">
                  Vector shows up where work happens. Vector connects early signals, identifies risks, and makes sure
                  blockers and delays never surface.
                </p>
                <div className="cta-actions meet-vector__cta">
                  <a className="btn-light" href={DEMO_CAL_URL} target="_blank" rel="noopener noreferrer">
                    See Vector in action
                  </a>
                </div>
              </div>
              <aside ref={meetSnippetRef} className="meet-vector-snippet" aria-label="Vector proactive message snippet">
                <div className="meet-vector-snippet__body">
                  <div className="meet-vector-snippet__meta">
                    <img
                      className="meet-vector-snippet__avatar"
                      src={vectorHqUrl}
                      width={48}
                      height={48}
                      alt="Vector avatar"
                    />
                    <span>Vector</span>
                    <span aria-hidden="true">·</span>
                    <span>now</span>
                  </div>
                  <div className="meet-vector-snippet__bubble">
                    Hey Sam !<br />
                    Saw checkout is still waiting on validation 🙂<br />
                    Want me to try to unblock things so we can ship today?
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <section className="section" id="stack">
          <div className="section-inner">
            <header className="text-center">
              <h2>
                Vector <span className="accent">understands</span> what’s happening
              </h2>
              <p className="sub mx-auto mt-7 max-w-2xl">And fixes it before you have to</p>
            </header>
            <div className="execution-flow" aria-label="Team thread and actions Vector takes across tools">
              <div className="execution-flow__chat">
                <div className="chat-card">
                  <div className="chat-shell">
                    <div className="chat-thread">
                      <div className="chat-block chat-row">
                        <img className="avatar" src={broUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span className="execution-flow__name">Sam</span>
                            <span className="execution-flow__time">10:02 AM</span>
                          </div>
                          <div className="bubble">Anyone reviewing the checkout PR?</div>
                        </div>
                      </div>
                      <div className="chat-block chat-row">
                        <img className="avatar" src={loreenUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span className="execution-flow__name">Lena</span>
                            <span className="execution-flow__time">10:04 AM</span>
                          </div>
                          <div className="bubble">I thought Alex had it</div>
                        </div>
                      </div>
                      <div className="chat-block chat-row">
                        <img className="avatar" src={heroOrgMichelleUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span className="execution-flow__name">Alex</span>
                            <span className="execution-flow__time">10:06 AM</span>
                          </div>
                          <div className="bubble">I'm on payments today, didn't see it</div>
                        </div>
                      </div>
                      <div className="chat-block chat-row">
                        <img className="avatar" src={broUrl} alt="" />
                        <div className="flex-1">
                          <div className="bubble-meta">
                            <span className="execution-flow__name">Sam</span>
                            <span className="execution-flow__time">10:09 AM</span>
                          </div>
                          <div className="bubble">It's been open since Monday 😬</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="execution-flow__bridge">
                <span className="execution-flow__cap execution-flow__cap--left" aria-hidden="true" />
                <div className="vector-label">Vector</div>
                <span className="execution-flow__cap execution-flow__cap--right" aria-hidden="true" />
              </div>
              <div className="execution-flow__actions">
                <div className="actions">
                  <div className="action">
                    <span className="action__logo" role="img" aria-label="Linear">
                      <LinearLogo className="action__logo-svg" />
                    </span>
                    <span className="action__text">Issue ownership clarified</span>
                  </div>
                  <div className="action">
                    <span className="action__logo" role="img" aria-label="GitHub">
                      <GitHubLogo className="action__logo-svg" />
                    </span>
                    <span className="action__text">Reviewer assigned to Alex</span>
                  </div>
                  <div className="action">
                    <span className="action__logo" role="img" aria-label="Notion">
                      <NotionLogo className="action__logo-svg" />
                    </span>
                    <span className="action__text">Release plan and ETA updated</span>
                  </div>
                  <div className="action">
                    <span className="action__logo" role="img" aria-label="Slack">
                      <SlackLogo className="action__logo-svg" />
                    </span>
                    <span className="action__text">Update shared with the manager</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="core-features">
          <div className="section-inner">
            <header className="text-center">
              <h2>
                Why <span className="accent">Vector</span>?
              </h2>
              <p className="sub mx-auto mt-7 max-w-2xl">Onboarding only takes five minutes.</p>
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

        <section className="section section-timeline" id="timeline-section" aria-labelledby="timeline-heading">
          <div className="section-inner">
            <header className="timeline-head text-center">
              <h2 id="timeline-heading">One timeline. Two realities.</h2>
            </header>
            <div className="timeline-compare">
              <div className="timeline-side timeline-side--before">
                <p className="timeline-compare-title timeline-compare-title--before" id="timeline-before-title">
                  Without Vector
                </p>
                <ol className="timeline timeline--before" id="timeline-before" aria-labelledby="timeline-before-title">
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Ping engineer for update</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Wait 3h → no answer</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Check Linear → still “In progress”</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Open PR → no reviewer assigned</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Ask in Slack → partial answer</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Hidden dependency surfaces late</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                    </div>
                    <span className="timeline-label">Follow up again tomorrow</span>
                  </li>
                </ol>
              </div>
              <div className="timeline-side timeline-side--after">
                <p className="timeline-compare-title timeline-compare-title--after" id="timeline-after-title">
                  With Vector
                </p>
                <ol className="timeline timeline--after" id="timeline-after" aria-labelledby="timeline-after-title">
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Follow-ups handled automatically</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Reviewers assigned instantly</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Blockers surfaced before they hit</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Dependencies resolved across teams</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Priorities continuously aligned</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot" />
                      <span className="timeline-line" aria-hidden="true" />
                    </div>
                    <span className="timeline-label">Next steps always clear</span>
                  </li>
                  <li>
                    <div className="timeline-col">
                      <span className="timeline-dot timeline-dot--done" />
                    </div>
                    <span className="timeline-label">Execution stays on track</span>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </section>

        <section className="section section-impact" id="impact" aria-labelledby="impact-heading">
          <div className="section-inner">
            <header className="impact-head text-center">
              <h2 id="impact-heading">
                Execution is <span className="accent">handled</span>.
              </h2>
            </header>
            <div className="impact-grid" aria-label="Manager impact metrics">
              <div className="impact-row impact-row--top">
                <article className="impact-item">
                  <p className="impact-value impact-value--accent">4h/day</p>
                  <p className="impact-copy">saved on reporting, follow-ups, and standups</p>
                </article>
                <article className="impact-item">
                  <p className="impact-value">Faster</p>
                  <p className="impact-copy">shipping, by catching drift earlier</p>
                </article>
                <article className="impact-item">
                  <p className="impact-value impact-value--accent">24/7</p>
                  <p className="impact-copy">coverage across Slack, GitHub, and Linear</p>
                </article>
              </div>
              <div className="impact-row-divider" aria-hidden="true" />
              <div className="impact-row impact-row--bottom">
                <article className="impact-item">
                  <p className="impact-value">Extra leverage</p>
                  <p className="impact-copy">without adding more meetings or oversight</p>
                </article>
                <article className="impact-item">
                  <p className="impact-value">
                    <span className="block">No</span>
                    <span className="block">Surprises</span>
                  </p>
                  <p className="impact-copy">from blockers, delays, and dependencies</p>
                </article>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="cta">
          <div className="section-inner">
            <div className="cta-card">
              <h2>
                <span className="block">Before it slips,</span>
                <span className="block" style={{ marginTop: "0.25rem" }}>
                  <span className="accent">Vector</span> is already on it.
                </span>
              </h2>
              <p className="sub mt-7 sm:mt-8 max-w-2xl mx-auto">
                Sounds exciting? <span style={{ fontWeight: 700, color: "var(--ink)" }}>Try Vector now.</span>
              </p>
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
                <Link className="btn-pill btn-pill--hero" to="/signup">
                  Get started
                </Link>
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
