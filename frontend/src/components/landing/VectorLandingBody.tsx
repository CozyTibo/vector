import { type ReactNode, useEffect, useRef } from "react";
import { Link } from "react-router-dom";

import vectorHeroAvatarUrl from "../../assets/logo.jpeg";
import "../../styles/vector-landing-scoped.css";
import { MeetVectorIntegrationsHub } from "./MeetVectorIntegrationsHub.tsx";

const DEMO_CAL_URL = "https://calendar.app.google/GcS9iPFBuL9XFzhc8";

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

const FAQ_ITEMS: ReadonlyArray<{ q: string; a: ReactNode }> = [
  {
    q: "Who is Vector for?",
    a: (
      <p>
        Engineering leaders and their managers, anyone responsible for delivery who ends up absorbing the
        coordination tax instead of shipping. Vector removes that overhead. No more firefighting. No more
        surprises. Lean delivery.
      </p>
    ),
  },
  {
    q: "How does Vector show up for me?",
    a: (
      <>
        <p>You don&apos;t go to Vector. Vector comes to you, entirely through Slack.</p>
        <p>
          A daily briefing every morning. A nudge in the right thread when something needs action. A sprint
          recap when you ask for it.
        </p>
        <p>No new tool. No new workflow. Just the right context at the right moment.</p>
      </>
    ),
  },
  {
    q: "How is Vector different from productivity tools?",
    a: (
      <>
        <p>
          Most tools make managers more informed. Vector makes managers less necessary for routine
          coordination.
        </p>
        <p>
          The difference is where the loop closes: with a dashboard, you still have to read it, interpret it,
          act. With Vector, the loop closes automatically. You&apos;re only notified when something needs a
          human decision, everything else is handled.
        </p>
      </>
    ),
  },
  {
    q: "How is Vector different from a Claude agent we could build ourselves?",
    a: (
      <p>
        Building the agent is the easy part. The hard part is knowing which signals predict a miss, which
        coordination patterns precede a slip, what healthy execution looks like, and encoding that into
        something that works reliably across engineering orgs. That&apos;s Vector&apos;s core product.
        You&apos;re not buying an LLM wrapper. You&apos;re buying a brain that understands how your team
        works.
      </p>
    ),
  },
  {
    q: "Does Vector read our Slack messages?",
    a: (
      <>
        <p>
          Yes, and this is deliberate. Most execution problems don&apos;t show up in Jira. They surface in a
          message that didn&apos;t get a reply, or a thread where a decision quietly shifted.
        </p>
        <p>
          Vector reads channel content to build a real picture of coordination. It&apos;s processed
          in-context, but never stored. Private messages are out of scope and remain private.
        </p>
      </>
    ),
  },
  {
    q: "Does Vector track individual performance?",
    a: (
      <p>
        No. Vector tracks coordination patterns: whether work is moving, where dependencies are forming, where
        blockers are accumulating. It doesn&apos;t score individuals, rank engineers, or produce performance
        ratings.
      </p>
    ),
  },
  {
    q: "How do we know our data is safe?",
    a: (
      <p>
        Our DPA explicitly prohibits Anthropic from using your data for AI training, limits data retention to
        what&apos;s needed to process a request, and lists every subprocessor with access. Infrastructure
        runs on AWS Ireland (SOC 2 Type II, ISO 27001, ISO 27701). If procurement needs to review it before
        signing, reach out at{" "}
        <a className="faq-link" href="mailto:victoire@angelcorp.ai">
          victoire@angelcorp.ai
        </a>
        .
      </p>
    ),
  },
];

const IMPACT_BLOCKS = [
  {
    accent: true,
    stat: "Focus",
    copy: "30% of your time back leading, not chasing updates.",
  },
  {
    accent: false,
    stat: "Act fast",
    copy: `The next best action, surfaced instantly.
No digging. No guessing. Just move.`,
  },
  {
    accent: true,
    stat: "Control",
    copy: `Fix how work flows, not just what's stuck.
Fewer escalations. Cleaner execution.`,
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

export function VectorLandingBody({ signedInWorkspaceCta }: VectorLandingBodyProps) {
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
                  Vector surfaces risks and guides your next steps based on live data from your team.
                </p>
                <div className="hero-cta-row">
                  <a className="btn-light" href={DEMO_CAL_URL} target="_blank" rel="noopener noreferrer">
                    Book a demo
                  </a>
                </div>
              </div>
            </div>
            <div className="hero-product">
              <div className="hero-product__slack-wrap">
                <LandingHeroSlackPreview />
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
                  Vector connects to the tools your team already uses and pushes risks, slowdowns, and concrete actions
                  to you in real time. You can approve each move in one go, without untangling every thread first.
                </p>
                <p className="sub meet-vector__support">
                  Instead of chasing updates across different sources and stakeholders, Vector brings everything
                  together so you can focus on delivery: you make the call on the next step, and it runs the
                  follow-through in your tools.
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
                      <MovesWorkForwardSlackPreview />
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
                      <span className="timeline-contrast__dot" aria-hidden="true" />
                      <p className="timeline-contrast__text">
                        {slot.time}. {slot.without}
                      </p>
                    </div>
                    <div className="timeline-contrast__side timeline-contrast__side--with">
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

        <section className="faq-strip" id="faq" aria-labelledby="faq-heading">
          <div className="faq-strip__inner">
            <header className="faq-strip__header">
              <h2 id="faq-heading">
                Frequently asked <span className="accent">questions</span>
              </h2>
            </header>
            <ul className="faq-list" role="list">
              {FAQ_ITEMS.map((item) => (
                <li key={item.q} className="faq-list__item">
                  <details className="faq-item">
                    <summary className="faq-item__q">
                      <span className="faq-item__q-text">{item.q}</span>
                      <span className="faq-item__icon" aria-hidden="true" />
                    </summary>
                    <div className="faq-item__a">{item.a}</div>
                  </details>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      <footer>
        <p>© {new Date().getFullYear()} Vector</p>
      </footer>
    </div>
  );
}
