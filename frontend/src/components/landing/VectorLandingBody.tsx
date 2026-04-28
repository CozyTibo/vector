import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import heroOrgMichelleUrl from "../../assets/hero-org-michelle.png";
import vectorHeroAvatarUrl from "../../assets/vector-white-bg.png";
import "../../styles/vector-landing-scoped.css";
import { MeetVectorIntegrationsHub } from "./MeetVectorIntegrationsHub.tsx";

const DEMO_CAL_URL = "https://calendar.app.google/GcS9iPFBuL9XFzhc8";

const HERO_CHAT_DELAYS_MS = [420, 580, 560, 1350, 920] as const;
const HERO_CHAT_STEP_COUNT = 6;

const EMPOWER_ORDER = [
  "managerInsights",
  "reportingAutomation",
  "peerReview",
  "staleThreadsEscalation",
  "driftDetection",
] as const;

type EmpowerKey = (typeof EMPOWER_ORDER)[number];

const EMPOWER_META: Record<
  EmpowerKey,
  { tabId: string; title: string; sub: string; bubbles: string[]; ariaLabel: string; time: string }
> = {
  managerInsights: {
    tabId: "empower-tab-manager-insights",
    title: "Manager insights",
    sub: "Delivery signal and how your people work together",
    ariaLabel: "Manager insights: pulse, signals, collaboration, insights, one priority",
    time: "",
    bubbles: [],
  },
  reportingAutomation: {
    tabId: "empower-tab-reporting-automation",
    title: "Reporting automation",
    sub: "Rollups on your rhythm, weekly, daily, or on milestones",
    ariaLabel: "Automated Notion weekly report with delivery, KPI, project, and drift updates",
    time: "7:01 AM",
    bubbles: [
      "Your weekly rollup is ready, with the same sections as last time.",
      "Shipped / slipped / next commitments, pulled from Linear + Slack with links back to source.",
      "Cadence is Mondays 7:00 your time. Want a second digest on Thursdays? I can add it.",
    ],
  },
  peerReview: {
    tabId: "empower-tab-peer-review",
    title: "Peer review",
    sub: "Reviews and approvals routed before work stalls",
    ariaLabel: "Peer review overview with strongest extracted signal per teammate pair",
    time: "11:08 AM",
    bubbles: [
      "Peer review nudge for the API gateway change.",
      "Two approvals still out: Francesco and Jordan. I sent each the diff + the two questions reviewers usually ask here.",
      "If neither lands by EOD, I’ll escalate to the EM with a one-line risk note.",
    ],
  },
  staleThreadsEscalation: {
    tabId: "empower-tab-stale-threads",
    title: "Stale threads & escalation",
    sub: "Quiet Slack, stuck threads summarized, then acted on",
    ariaLabel: "Stale thread in Slack: Vector summarizes #eng-checkout and offers to assign and clarify the date",
    time: "2:26 PM",
    bubbles: [],
  },
  driftDetection: {
    tabId: "empower-tab-drift-detection",
    title: "Drift detection",
    sub: "Scope and ownership shifts before they hit the date",
    ariaLabel: "Drift detection: Vector nudges manager on a stale checkout ticket",
    time: "2:14 PM",
    bubbles: [],
  },
};

function StaleThreadsEscalationChatShowcase() {
  const meta = EMPOWER_META.staleThreadsEscalation;
  return (
    <div className="chat-card chat-card--compact chat-card--escalation" role="region" aria-label={meta.ariaLabel}>
      <div className="chat-shell">
        <div className="chat-head">
          <strong>#eng-checkout</strong>
          <span className="muted">·</span>
          <span className="muted">Stale thread</span>
        </div>
        <div className="chat-thread">
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>{meta.time}</span>
              </div>
              <div className="bubble bubble--escalation-brief">
                <p className="bubble--escalation-brief__lead">
                  Sam, quick heads up - thread in <strong>#eng-checkout</strong> has been open 26 hours, no owner
                  assigned.
                </p>
                <div className="bubble--escalation-brief__section">
                  <p className="bubble--escalation-brief__kicker">What’s happening:</p>
                  <p className="bubble--escalation-brief__support">
                    payment webhook failing in staging, 500 errors confirmed by 2 engineers.
                  </p>
                </div>
                <div className="bubble--escalation-brief__section">
                  <p className="bubble--escalation-brief__kicker">What’s unclear:</p>
                  <ol className="bubble--escalation-brief__ol">
                    <li>ownership (Alex raised it, Sam pushed back, no one else claimed it)</li>
                    <li>release date (Linear says Monday, team thinks Friday)</li>
                  </ol>
                </div>
                <div className="bubble--escalation-brief__section">
                  <p className="bubble--escalation-brief__kicker">Risk:</p>
                  <p className="bubble--escalation-brief__support">
                    if it’s the Stripe webhook and release is actually Friday, checkout ships broken.
                  </p>
                </div>
                <p className="bubble--escalation-brief__cta">
                  Want me to assign and clarify the date ? 🙏🏻
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DriftDetectionChatShowcase() {
  return (
    <div
      className="chat-card chat-card--compact"
      role="region"
      aria-label={EMPOWER_META.driftDetection.ariaLabel}
    >
      <div className="chat-shell">
        <div className="chat-head">
          <strong>Checkout</strong>
          <span className="muted">·</span>
          <span className="muted">Stale ticket</span>
        </div>
        <div className="chat-thread">
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:14 PM</span>
              </div>
              <div className="bubble">
                Hey Sam, noticed that ticket on check-out has been sitting in &quot;in progress&quot; for 7 days now.
                Should we assign to someone else?
              </div>
            </div>
          </div>
          <div className="chat-block chat-row--alex is-visible">
            <div className="bubble-meta bubble-meta--alex">
              <img className="avatar" src={heroOrgMichelleUrl} alt="" />
              <span style={{ fontSize: 14, fontWeight: 600 }}>Sam</span>
              <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:15 PM</span>
            </div>
            <div className="bubble bubble--alex">yes, who&apos;s on call?</div>
          </div>
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:15 PM</span>
              </div>
              <div className="bubble">Alex is, want me to hand over?</div>
            </div>
          </div>
          <div className="chat-block chat-row--alex is-visible">
            <div className="bubble-meta bubble-meta--alex">
              <img className="avatar" src={heroOrgMichelleUrl} alt="" />
              <span style={{ fontSize: 14, fontWeight: 600 }}>Sam</span>
              <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:16 PM</span>
            </div>
            <div className="bubble bubble--alex">👍🏻</div>
          </div>
          <div className="chat-block chat-row is-visible">
            <img className="avatar" src={vectorHeroAvatarUrl} alt="" />
            <div className="flex-1">
              <div className="bubble-meta">
                <span style={{ fontSize: 14, fontWeight: 600 }}>Vector</span>
                <span style={{ fontSize: 13, color: "#a1a1aa" }}>2:16 PM</span>
              </div>
              <div className="bubble">
                Done, pinged Alex with context. I&apos;ll follow up if it stalls!
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportingAutomationShowcase() {
  return (
    <div className="ra-showcase" role="region" aria-label={EMPOWER_META.reportingAutomation.ariaLabel}>
      <div className="ra-page">
        <header className="ra-head">
          <p className="ra-head__eyebrow">Notion weekly report</p>
          <h3 className="ra-head__title">Core Product delivery digest - last 7 days</h3>
          <p className="ra-head__meta">Teams: Checkout + Core Platform + Auth | Manager: Sam</p>
        </header>

        <div className="ra-kpi-row" aria-label="Weekly KPI summary">
          <div className="ra-kpi">
            <p className="ra-kpi__label">Delivery</p>
            <p className="ra-kpi__value">9 shipped / 2 at risk</p>
          </div>
          <div className="ra-kpi">
            <p className="ra-kpi__label">PR quality</p>
            <p className="ra-kpi__value">31% need rework</p>
          </div>
          <div className="ra-kpi">
            <p className="ra-kpi__label">Escalations</p>
            <p className="ra-kpi__value">3 stale threads flagged</p>
          </div>
        </div>

        <div className="ra-grid">
          <article className="ra-card">
            <p className="ra-card__label">Projects</p>
            <p className="ra-card__text">
              <strong>Payments architecture</strong> design docs approved, implementation starts Monday.
            </p>
            <p className="ra-card__text">
              <strong>Auth migration</strong> still unowned after Alex shifted to payments design.
            </p>
          </article>

          <article className="ra-card">
            <p className="ra-card__label">Delivery and risk</p>
            <p className="ra-card__text">
              Checkout and Core are queueing on Sam for fixes and deployment coordination.
            </p>
            <p className="ra-card__text">If this dependency holds, Friday release confidence drops from 82% to 61%.</p>
          </article>

          <article className="ra-card">
            <p className="ra-card__label">Drift signals</p>
            <p className="ra-card__text">
              Rebecca&apos;s PRs regularly require multiple reworks before merge, slowing review throughput.
            </p>
            <p className="ra-card__text">Vector detected repeat spec gaps across 3 PRs in checkout webhook logic.</p>
          </article>

          <article className="ra-card">
            <p className="ra-card__label">Recommended manager actions</p>
            <p className="ra-card__text">Assign auth migration owner this week and rebalance deploy handoffs from Sam.</p>
            <p className="ra-card__text">Schedule a 20-min design-review checkpoint with Rebecca before implementation.</p>
          </article>
        </div>
      </div>
    </div>
  );
}

function PeerReviewShowcase() {
  const reviews = [
    {
      reviewer: "Sam",
      reviewee: "Rebecca",
      signal: "Most common thread: handoffs to Rebecca keep missing a clear done bar, seen in 4 of 5 recent reviews of her work.",
    },
    {
      reviewer: "Alex",
      reviewee: "Sam",
      signal: "Strongest positive signal: Sam’s diffs ship with context, test plan, and rollout in one place, fewer review round trips.",
    },
    {
      reviewer: "Rebecca",
      reviewee: "Tereza",
      signal: "Pattern in answers: after a plan change, Tereza posts a same day update in writing, and duplicate work shows up less in follow on reviews.",
    },
    {
      reviewer: "Tereza",
      reviewee: "Alex",
      signal: "Top risk called out: reviews keep asking for edge case QA, not just happy path, on Alex’s core path changes.",
    },
  ] as const;

  return (
    <div className="pr-showcase" role="region" aria-label={EMPOWER_META.peerReview.ariaLabel}>
      <header className="pr-head">
        <p className="pr-head__eyebrow">Peer review map</p>
        <h3 className="pr-head__title">This month&apos;s peer reviews (4 teammates)</h3>
      </header>
      <div className="pr-grid">
        {reviews.map((row) => (
          <article key={`${row.reviewer}-${row.reviewee}`} className="pr-row">
            <p className="pr-row__pair">
              <span className="pr-row__name">{row.reviewer}</span>
              <span className="pr-row__arrow" aria-hidden="true">
                →
              </span>
              <span className="pr-row__name">{row.reviewee}</span>
            </p>
            <PeerReviewSignalLine text={row.signal} />
          </article>
        ))}
      </div>
    </div>
  );
}

function PeerReviewSignalLine({ text }: { text: string }) {
  const i = text.indexOf(":");
  if (i === -1) {
    return <p className="pr-row__signal">{text}</p>;
  }
  const lead = text.slice(0, i + 1).trimEnd();
  const body = text.slice(i + 1).trimStart();
  return (
    <p className="pr-row__signal">
      <strong className="pr-row__signal-lead">{lead}</strong> {body}
    </p>
  );
}

function ManagerInsightsShowcase() {
  const sections = [
    {
      label: "Pulse",
      body: "9 PRs shipped, 2 stuck on review.",
    },
    {
      label: "Signal",
      body: "Rebecca’s PRs often require multiple reworks before getting merged.",
    },
    {
      label: "Collaboration",
      body: "Checkout and Core are waiting on Sam for fixes and deployments. Work is queueing up.",
    },
    {
      label: "Insight",
      body: "Alex is focusing on system design for the new payments architecture, leaving the auth migration without a clear owner.",
    },
    {
      label: "Close",
      body: "One priority needs your call this week: auth migration ownership.",
    },
  ] as const;

  return (
    <div
      className="mis-showcase"
      role="region"
      aria-label={EMPOWER_META.managerInsights.ariaLabel}
    >
      <div className="mis-showcase__top">
        <p className="mis-showcase__eyebrow">Manager insights</p>
        <h3 className="mis-showcase__title">This week, Vector surfaced...</h3>
      </div>
      <div className="mis-stack">
        {sections.map((section) => (
          <article key={section.label} className="mis-section">
            <p className="mis-section__label">{section.label}</p>
            <p className="mis-section__body">{section.body}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function EmpowerPanel({ feature }: { feature: EmpowerKey }) {
  switch (feature) {
    case "managerInsights":
      return <ManagerInsightsShowcase />;
    case "reportingAutomation":
      return <ReportingAutomationShowcase />;
    case "peerReview":
      return <PeerReviewShowcase />;
    case "staleThreadsEscalation":
      return <StaleThreadsEscalationChatShowcase />;
    case "driftDetection":
      return <DriftDetectionChatShowcase />;
    default:
      return null;
  }
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
  const [empower, setEmpower] = useState<EmpowerKey>("managerInsights");

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

        <section className="section" id="core-features">
          <div className="section-inner">
            <header className="text-center">
              <h2>
                How <span className="accent">Vector</span> shows up for you
              </h2>
            </header>
            <div className="empowers-split">
              <div className="empowers-nav" role="tablist" aria-label="Vector capabilities">
                {EMPOWER_ORDER.map((key) => {
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
                  Of your week back, spent leading, not chasing updates.
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
                  Project radar, blind spots surface before they cost you.
                </p>
              </article>
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
