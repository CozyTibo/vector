import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import vectorHqShowcaseUrl from "../../assets/vector-hq.png";
import {
  landingAccentChipPurple,
  landingAccentText,
  landingTitleKeywordGradient,
} from "./landingBrandPalette";

const panel =
  "rounded-2xl border border-zinc-200/80 bg-white/90 shadow-[0_12px_48px_-20px_rgba(15,23,42,0.08)] backdrop-blur-xl";
/** Neutral card shadow (avoid pink glow halos) */
const glowPurple = "shadow-[0_20px_50px_-32px_rgba(15,23,42,0.1)]";
/** Section vertical rhythm - tight enough to scroll comfortably */
const sectionPad = "py-14 sm:py-16 lg:py-20";

/** “How Vector reconstructs execution” - off until we ship the narrative again */
const showHowVectorReconstructsSection = false;

/** “Why execution breaks” - hidden until we ship this narrative again */
const showProblemSection = false;

/** “The questions Vector answers for you” (three pillars) - hidden; preview lives in Meet Vector */
const showWhatVectorKnowsSection = false;

/** Same typography as Vision (“Execution should be observable”) */
const sectionTitleClass =
  "w-full text-4xl font-bold tracking-[-0.03em] text-zinc-900 sm:text-5xl sm:leading-[1.06] lg:text-6xl lg:leading-[1.02]";

/** Section title block: top of section, left-aligned */
const sectionHeaderClass = "w-full text-left lg:pl-2";

/** Body copy - matches Vision (“Execution should be observable”) left column */
const sectionProseBorder = "border-l-2 border-[#F5C8E0]/90 pl-7 sm:border-[#F5C8E0] sm:pl-9";
const sectionProseStack = "space-y-6 sm:space-y-7";
export const sectionProseMuted = "text-pretty text-lg leading-snug text-zinc-600 sm:text-xl";
const sectionProseBody = "text-pretty text-lg font-medium leading-snug text-zinc-800 sm:text-xl";
const sectionProseStrong = "text-pretty text-lg font-semibold leading-snug text-zinc-950 sm:text-xl";

/** Lead / subtitle under a section H2 (same scale as Vision body) */
const sectionLead = sectionProseMuted;

/** Card titles in problem, signals, who, feature preview */
const cardTitleClass = "text-lg font-semibold leading-snug text-zinc-900 sm:text-xl";

/** Card supporting copy */
const cardBodyClass = "text-base leading-snug text-zinc-600 sm:text-lg";

/** Comparison / bullet lists at marketing body scale */
const sectionListEmphasis = "text-lg font-medium leading-snug text-zinc-800 sm:text-xl";

/** CTA supporting copy and steps */
const sectionCtaMuted = "text-pretty text-lg leading-snug text-zinc-600 sm:text-xl";
const sectionCtaList = "text-lg leading-snug text-zinc-700 sm:text-xl";

/** Fragmented-tools card only - tight story: Slack → GitHub → Linear */
const scatteredToolChips: { short: string; color: "purple" | "teal" | "zinc" | "amber" }[] = [
  { short: "Slack", color: "purple" },
  { short: "GitHub", color: "zinc" },
  { short: "Linear", color: "teal" },
];

/** Stack diagram - tools that feed Vector */
const pipelineIntegrationChipNames = [
  "Slack",
  "GitHub",
  "Linear",
  "Notion",
  "Jira",
  "Internal tools",
] as const;

const titleAccent = {
  howVector: landingTitleKeywordGradient,
  core: landingTitleKeywordGradient,
  problem: landingTitleKeywordGradient,
  agent: landingTitleKeywordGradient,
  threeThings: landingTitleKeywordGradient,
  stack: landingTitleKeywordGradient,
} as const;

/** Problem section - 2×2 cards, concrete copy, max ~18 words per body */
const PROBLEM_CARDS: {
  title: string;
  body: string;
  dot: "violet" | "teal" | "amber" | "fuchsia";
}[] = [
  {
    title: "Scattered signals",
    body: "Connected tools fill dashboards; every chart still needs a human to decode the next move.",
    dot: "violet",
  },
  {
    title: "Instinct over signal",
    body: "Problems show up as gut feel and hallway talk, not as reliable signals you can trust.",
    dot: "teal",
  },
  {
    title: "Subjective status",
    body: "Updates pass through layers of interpretation. By the time leadership sees them, the signal is diluted.",
    dot: "amber",
  },
  {
    title: "Hidden dependencies",
    body: "Cross-team dependencies stay invisible until teams collide, when delays are already expensive.",
    dot: "fuchsia",
  },
];

function useInView<T extends HTMLElement>(threshold = 0.15) {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) setVisible(true);
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, visible };
}

function ScrollFade({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const { ref, visible } = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out motion-reduce:transition-none ${visible ? "translate-y-0 opacity-100" : "translate-y-5 opacity-0"} ${className}`}
    >
      {children}
    </div>
  );
}

function ToolChip({ name, color }: { name: string; color: "purple" | "teal" | "zinc" | "amber" }) {
  const c =
    color === "purple"
      ? landingAccentChipPurple
      : color === "teal"
        ? "border-zinc-300/80 bg-zinc-100/90 text-zinc-800"
        : color === "amber"
          ? "border-amber-300/50 bg-amber-500/10 text-amber-900"
          : "border-zinc-200/80 bg-zinc-50 text-zinc-700";
  return (
    <div
      className={`relative z-[1] flex min-w-[5.5rem] max-w-[11rem] items-center justify-center rounded-xl border px-3 py-2 text-center text-[10px] font-semibold leading-tight tracking-tight sm:text-[11px] ${c} transition-transform duration-300 hover:-translate-y-0.5 hover:shadow-md`}
    >
      {name}
    </div>
  );
}

function SectionShell({
  id,
  children,
  className = "",
  divider,
}: {
  id?: string;
  children: React.ReactNode;
  className?: string;
  divider?: boolean;
}) {
  return (
    <section id={id} className={`scroll-mt-28 ${className}`}>
      <div className="mx-auto max-w-[96rem] px-5 sm:px-8">
        {divider ? (
          <div
            className="mb-8 h-px w-full bg-gradient-to-r from-transparent via-zinc-300/40 to-transparent sm:mb-10"
            aria-hidden
          />
        ) : null}
        {children}
      </div>
    </section>
  );
}

/* -- Pipeline diagrams (shared) -- */
function PipelineFlowArrow() {
  return (
    <div className="flex justify-center text-zinc-300">
      <span className="text-xl leading-none sm:text-2xl">↓</span>
    </div>
  );
}

function PipelineProductVisual({ size = "full" }: { size?: "full" | "mini" }) {
  const pad = size === "mini" ? "p-5 sm:p-6" : "p-8 sm:p-10";
  const chip =
    size === "mini"
      ? "rounded-md px-2 py-1 text-[9px] font-semibold leading-tight text-zinc-700 sm:text-[10px]"
      : "rounded-lg px-2.5 py-1.5 text-[10px] font-semibold leading-tight text-zinc-700 shadow-sm sm:text-[11px]";
  const title = size === "mini" ? "text-xs" : "text-sm";
  return (
    <div className={`relative space-y-4 sm:space-y-6 ${panel} ${pad}`}>
      <div className="flex flex-wrap justify-center gap-x-1.5 gap-y-2 sm:gap-x-2 sm:gap-y-2.5">
        {pipelineIntegrationChipNames.map((name) => (
          <span key={name} className={`border border-zinc-200/80 bg-white ${chip}`}>
            {name}
          </span>
        ))}
      </div>
      <PipelineFlowArrow />
      <p className={`text-center font-semibold text-zinc-900 ${title}`}>Execution signals</p>
      <PipelineFlowArrow />
      <div className="rounded-xl border border-zinc-200/80 bg-zinc-50/80 px-4 py-3 text-center sm:py-4">
        <p className={`font-bold text-zinc-900 ${size === "mini" ? "text-xs" : "text-sm"}`}>Vector</p>
        <p className={`mt-1 text-zinc-900 ${size === "mini" ? "text-[10px]" : "text-xs"}`}>
          Understands execution continuously
        </p>
      </div>
      <PipelineFlowArrow />
      <p className={`text-center font-semibold text-zinc-900 ${title}`}>Insights · Reports · Recommendations</p>
    </div>
  );
}

/** Fragmented tools + flow + Vector (reused from legacy Problem section) */
function FragmentedToolsVisual() {
  return (
    <div className="relative">
      <div className={`relative ${panel} p-5 sm:p-6`}>
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">Fragmented tools</p>
        <div className="relative mt-6 flex flex-wrap items-center justify-center gap-2 sm:gap-3">
          {scatteredToolChips.map((c, i) => (
            <ToolChip key={`${c.short}-${i}`} name={c.short} color={c.color} />
          ))}
        </div>
        <svg className="mx-auto mt-4 h-16 w-full max-w-xs text-zinc-300/90" aria-hidden>
          <path
            d="M 20 4 L 80 4 L 80 28 L 50 28 L 50 52 L 100 52"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeDasharray="4 4"
            className="animate-[dash_1.2s_linear_infinite] motion-reduce:animate-none"
          />
        </svg>
        <div className="mt-2 space-y-1 text-center text-xs font-medium leading-snug text-zinc-500 sm:space-y-1.5 sm:text-sm">
          <p>Slack discussion</p>
          <p className="text-xs leading-none text-zinc-400 sm:text-sm">↓</p>
          <p>GitHub PR opened</p>
          <p className="text-xs leading-none text-zinc-400 sm:text-sm">↓</p>
          <p className="text-amber-700/90">No Linear issue</p>
          <p className="text-xs leading-none text-zinc-400 sm:text-sm">↓</p>
          <p className="font-semibold text-zinc-700">Execution unclear</p>
        </div>
        <div className="mt-8 border-t border-dashed border-zinc-200/80 pt-6">
          <div
            className={`relative overflow-hidden rounded-xl border border-zinc-200/70 bg-white p-4 shadow-sm ${glowPurple}`}
          >
            <p className={`text-[10px] font-semibold uppercase tracking-widest ${landingAccentText}`}>Vector</p>
            <p className="mt-2 text-sm font-semibold text-zinc-900">Execution signal detected</p>
            <p className="mt-1 text-xs font-medium text-zinc-600">Untracked work</p>
            <p className="mt-2 font-mono text-[11px] text-zinc-600">
              Slack → GitHub PR → <span className="text-amber-700">no Linear issue</span>
            </p>
          </div>
        </div>
      </div>
      <style>{`
        @keyframes dash { to { stroke-dashoffset: -16; } }
      `}</style>
    </div>
  );
}

/* -- How Vector reconstructs (fragmented tools visual) -- */
function HowVectorReconstructsSection() {
  return (
    <SectionShell id="how-vector" divider className={sectionPad}>
      <ScrollFade>
        <header className={sectionHeaderClass}>
          <h2 className={`${sectionTitleClass} max-w-4xl`}>
            How <span className={landingAccentText}>Vector</span>{" "}
            <span className={titleAccent.howVector}>reconstructs</span> execution
          </h2>
        </header>
        <div className="mt-12 grid items-start gap-12 lg:grid-cols-2 lg:gap-14">
          <div className="max-w-2xl lg:pl-2 lg:pr-4">
            <div className={sectionProseBorder}>
              <div className={sectionProseStack}>
                <p className={sectionProseMuted}>Work today is scattered across tools.</p>
                <ul className={`space-y-2 ${sectionProseBody}`}>
                  <li>Chat, docs, meetings & recordings</li>
                  <li>Code, reviews, planning, builds & automation</li>
                  <li>CRM & customers</li>
                </ul>
                <p className={sectionProseMuted}>Signals appear everywhere, but they never connect.</p>
                <p className={sectionProseBody}>
                  Vector connects these signals and reconstructs how work actually moves.
                </p>
              </div>
            </div>
          </div>
          <FragmentedToolsVisual />
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

type CoreRoleId = "executive" | "leaders" | "teams";

const CORE_ROLE_TABS: { id: CoreRoleId; label: string }[] = [
  { id: "executive", label: "Executive" },
  { id: "leaders", label: "Engineering & Product Leaders" },
  { id: "teams", label: "Teams" },
];

const CORE_ROLE_CONTEXT: Record<CoreRoleId, ReactNode> = {
  executive: <>How Vector helps leaders stay ahead of execution</>,
  leaders: <>How Vector helps managers run teams with clarity</>,
  teams: <>How Vector helps teams stay focused on what matters</>,
};

/** Minimal monochrome strokes — symbolic only, not decorative mockups */
type CoreBenefitIconId =
  | "target"
  | "alert"
  | "chart"
  | "inbox"
  | "pulse"
  | "link"
  | "trend"
  | "coach"
  | "orbit"
  | "stream"
  | "list"
  | "shield";

function CoreBenefitIcon({ id, className }: { id: CoreBenefitIconId; className?: string }) {
  const c = `h-5 w-5 shrink-0 stroke-current ${className ?? ""}`;
  switch (id) {
    case "target":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="9" strokeWidth="1.5" />
          <circle cx="12" cy="12" r="4.5" strokeWidth="1.5" />
          <circle cx="12" cy="12" r="1.25" fill="currentColor" stroke="none" />
        </svg>
      );
    case "alert":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 8.5v5M12 17h.01M10.3 4.8L3.2 17.5c-.5.9.1 2 1.1 2h15.4c1 0 1.6-1.1 1.1-2l-7.1-12.7c-.5-.9-1.7-.9-2.2 0z"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "chart":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M4 19V5M4 19h16M8 17V9M12 17v-6M16 17v-3" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "inbox":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 6a2 2 0 012-2h12a2 2 0 012 2v12l-4-4H8l-4 4V6z"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path d="M9 10h6" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "pulse":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 12h3l2-6 4 12 2-6h5"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "link":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M10 13a5 5 0 007.1 0l1.4-1.4a5 5 0 00-7.1-7.1L9 6M14 11a5 5 0 00-7.1 0L5.5 12.4a5 5 0 007.1 7.1L15 18"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      );
    case "trend":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M4 16l4-4 4 4 8-8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M16 8h4v4" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "coach":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M8 11a4 4 0 118 0v1.5c0 1.1-.9 2-2 2h-1M8 11V9M16 11V9"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path d="M6 20h12" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "orbit":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="3" strokeWidth="1.5" />
          <ellipse cx="12" cy="12" rx="9" ry="4.5" strokeWidth="1.5" transform="rotate(-25 12 12)" />
        </svg>
      );
    case "stream":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M6 8h12M6 12h8M6 16h10" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "list":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M9 6h12M9 12h12M9 18h12M5 6h.01M5 12h.01M5 18h.01" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "shield":
      return (
        <svg className={c} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 3l7 4v5c0 5-3 9-7 10-4-1-7-5-7-10V7l7-4z"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return null;
  }
}

type CoreValueBlock = {
  icon: CoreBenefitIconId;
  title: string;
  titleHighlight: string;
  sentence: string;
};

const CORE_VALUE_BLOCKS_BY_ROLE: Record<CoreRoleId, readonly CoreValueBlock[]> = {
  executive: [
    {
      icon: "target",
      title: "See what actually needs attention",
      titleHighlight: "attention",
      sentence: "Vector filters the noise and highlights what leaders actually need to look at.",
    },
    {
      icon: "alert",
      title: "Spot risks before they escalate",
      titleHighlight: "risks",
      sentence: "Surface dependencies and delays early, while you still have room to act.",
    },
    {
      icon: "chart",
      title: "Decide from real execution signals",
      titleHighlight: "execution signals",
      sentence: "Ground decisions in how work is really moving, not chasing updates.",
    },
    {
      icon: "inbox",
      title: "Automatic leadership updates",
      titleHighlight: "leadership",
      sentence: "Clear briefings for leadership without pulling teams into another status cycle.",
    },
  ],
  leaders: [
    {
      icon: "pulse",
      title: "Real-time signals from your teams",
      titleHighlight: "signals",
      sentence: "Blockers and drift surface instantly from the tools your teams already use.",
    },
    {
      icon: "link",
      title: "Stop chasing updates",
      titleHighlight: "updates",
      sentence: "PRs, tickets, and threads, connected without manual roll-ups.",
    },
    {
      icon: "trend",
      title: "Detect execution drift early",
      titleHighlight: "execution drift",
      sentence: "Catch slowdowns and dependency pile-ups before the date slips.",
    },
    {
      icon: "coach",
      title: "More time for coaching and strategy",
      titleHighlight: "strategy",
      sentence: "Less status gathering; more coaching and direction.",
    },
  ],
  teams: [
    {
      icon: "orbit",
      title: "A manager that is always available",
      titleHighlight: "available",
      sentence: "Always-on help surfacing what needs attention next.",
    },
    {
      icon: "stream",
      title: "Less reporting",
      titleHighlight: "reporting",
      sentence: "Your work signals replace endless “quick status” pings.",
    },
    {
      icon: "list",
      title: "Clear priorities",
      titleHighlight: "priorities",
      sentence: "Blockers and priorities in one clear view.",
    },
    {
      icon: "shield",
      title: "Fewer interruptions",
      titleHighlight: "interruptions",
      sentence: "Leaders get visibility without pinging you all day.",
    },
  ],
};

function CoreBenefitCardTitle({ title, highlight }: { title: string; highlight: string }) {
  if (!highlight || !title.includes(highlight)) {
    return <>{title}</>;
  }
  const i = title.indexOf(highlight);
  return (
    <>
      {title.slice(0, i)}
      <span className={landingTitleKeywordGradient}>{highlight}</span>
      {title.slice(i + highlight.length)}
    </>
  );
}

function CoreFeaturesSection() {
  const [role, setRole] = useState<CoreRoleId>("leaders");
  const blocks = CORE_VALUE_BLOCKS_BY_ROLE[role];
  const roleLabel = CORE_ROLE_TABS.find((t) => t.id === role)?.label ?? role;
  return (
    <SectionShell id="core-features" divider className={sectionPad}>
      <ScrollFade>
        <header className={sectionHeaderClass}>
          <h2 className={`${sectionTitleClass} max-w-4xl`}>
            <span className={landingTitleKeywordGradient}>Vector</span> empowers your teams
          </h2>
          <p className={`mt-6 max-w-2xl text-pretty ${sectionLead}`}>
            Same teammate, three lenses. Pick your role to see how Vector shows up for you.
          </p>
          <div className="mt-10 pb-2">
            <div
              role="tablist"
              aria-label="Role"
              className="inline-flex w-full max-w-full flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-zinc-50/45 p-2 shadow-[0_2px_24px_-16px_rgba(15,23,42,0.06)] backdrop-blur-md sm:w-auto sm:max-w-none sm:flex-row sm:flex-nowrap sm:rounded-full sm:p-1.5 sm:gap-1"
            >
              {CORE_ROLE_TABS.map((r) => {
                const active = role === r.id;
                return (
                  <button
                    key={r.id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setRole(r.id)}
                    className={`relative rounded-2xl px-5 py-3.5 text-left text-[15px] font-semibold transition-[color,transform,box-shadow,background-color] duration-200 ease-out sm:rounded-full sm:px-6 sm:py-3.5 sm:text-base ${
                      active
                        ? "bg-white text-zinc-900 shadow-sm ring-1 ring-zinc-200/80"
                        : "text-zinc-500 hover:bg-white/40 hover:text-zinc-800"
                    }`}
                  >
                    <span className={active ? "text-zinc-900" : "text-zinc-500"}>{r.label}</span>
                    {active ? (
                      <span
                        className="pointer-events-none absolute bottom-1.5 left-1/2 h-0.5 w-[72%] max-w-[10rem] -translate-x-1/2 rounded-full bg-zinc-900 sm:bottom-2"
                        aria-hidden
                      />
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        <div className="relative mt-11 lg:pl-2">
          <div key={role} className="relative z-[2] mb-5 max-w-2xl sm:mb-6">
            <p className="text-sm font-medium leading-snug text-zinc-500 sm:text-[15px]">
              {CORE_ROLE_CONTEXT[role]}
            </p>
          </div>

          <div
            className="relative"
            role="region"
            aria-label={`${roleLabel}: what Vector delivers`}
          >
            <div
              key={role}
              className="relative z-[1] motion-reduce:animate-none grid grid-cols-1 gap-6 sm:grid-cols-2 sm:gap-7 lg:gap-8 animate-[coreRoleContent_0.2s_ease-out_both]"
            >
            {blocks.map((b, i) => (
              <article
                key={b.title}
                style={{ animationDelay: `${i * 32}ms` }}
                className="core-benefit-card group relative rounded-2xl border border-zinc-200/70 bg-white transition-[transform,box-shadow] duration-300 ease-out motion-reduce:translate-y-0 motion-reduce:opacity-100 hover:-translate-y-1 hover:shadow-[0_20px_50px_-28px_rgba(15,23,42,0.12)] shadow-[0_12px_40px_-28px_rgba(15,23,42,0.07)] sm:min-h-[12.5rem]"
              >
                <div className="flex h-full min-h-[inherit] flex-col justify-center rounded-[calc(1rem-1px)] px-9 py-9 text-left sm:px-10 sm:py-10 lg:px-11 lg:py-10">
                  <div className="flex items-start gap-3.5 sm:gap-4">
                    <span
                      className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-zinc-200/60 bg-zinc-50/90 text-zinc-400 transition-colors duration-200 group-hover:border-zinc-200/80 group-hover:bg-white group-hover:text-zinc-500"
                      aria-hidden
                    >
                      <CoreBenefitIcon id={b.icon} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-xl font-bold leading-snug tracking-tight text-zinc-900 sm:text-2xl">
                        <CoreBenefitCardTitle title={b.title} highlight={b.titleHighlight} />
                      </h3>
                      <p className="mt-3 max-w-[26rem] text-pretty text-base leading-snug text-zinc-600 sm:text-[1.05rem] sm:leading-snug">
                        {b.sentence}
                      </p>
                    </div>
                  </div>
                </div>
              </article>
            ))}
            </div>
          </div>
        </div>

        <style>{`
          @keyframes coreRoleContent {
            from { transform: translateY(6px); }
            to { transform: translateY(0); }
          }
          @keyframes coreCardStagger {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @media (prefers-reduced-motion: no-preference) {
            .core-benefit-card {
              animation: coreCardStagger 0.48s ease-out both;
            }
          }
        `}</style>
      </ScrollFade>
    </SectionShell>
  );
}

function problemCardDotClass(dot: (typeof PROBLEM_CARDS)[number]["dot"]) {
  switch (dot) {
    case "violet":
      return "bg-[#E878BE] shadow-[0_0_0_3px_rgba(232,120,190,0.25)]";
    case "teal":
      return "bg-sky-500 shadow-[0_0_0_3px_rgba(14,165,233,0.22)]";
    case "amber":
      return "bg-amber-500 shadow-[0_0_0_3px_rgba(245,158,11,0.2)]";
    case "fuchsia":
      return "bg-indigo-600 shadow-[0_0_0_3px_rgba(79,70,229,0.22)]";
  }
}

/* -- Problem (below hero) -- */
function ProblemSection() {
  return (
    <SectionShell id="problem" divider className={sectionPad}>
      <ScrollFade>
        <header className={sectionHeaderClass}>
          <h2 className={`${sectionTitleClass} max-w-4xl`}>
            Why execution <span className={titleAccent.problem}>breaks</span>
          </h2>
          <div className="mt-6 max-w-2xl space-y-6 sm:space-y-7 lg:pl-2">
            <p className={sectionProseMuted}>Execution signals exist everywhere.</p>
            <p className={sectionProseStrong}>
              But leaders spend their time interpreting dashboards instead of making decisions.
            </p>
          </div>
        </header>
        <div className="mt-10 grid grid-cols-1 gap-4 sm:mt-12 sm:grid-cols-2">
          {PROBLEM_CARDS.map((item) => (
            <div
              key={item.title}
              className="rounded-xl border border-zinc-200/55 bg-white/75 p-5 shadow-[0_8px_32px_-22px_rgba(15,23,42,0.08)] backdrop-blur-sm transition-transform duration-300 hover:-translate-y-0.5 hover:border-zinc-200/80 hover:shadow-[0_12px_40px_-24px_rgba(15,23,42,0.1)]"
            >
              <div className="flex items-start gap-3">
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${problemCardDotClass(item.dot)}`}
                  aria-hidden
                />
                <div className="min-w-0">
                  <p className={cardTitleClass}>{item.title}</p>
                  <p className={`mt-2 ${cardBodyClass}`}>{item.body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

/* -- Meet Vector (hero avatar) -- */
function MeetVectorAvatarShowcase() {
  return (
    <div className="relative mx-auto w-full max-w-[18rem] translate-x-1.5 sm:max-w-[20rem] sm:translate-x-2 lg:max-w-[24rem] lg:translate-x-5 xl:max-w-[26rem] xl:translate-x-6">
      <div
        className={`relative overflow-hidden rounded-3xl border border-zinc-200/80 bg-white shadow-[0_20px_50px_-32px_rgba(15,23,42,0.1)] ring-1 ring-inset ring-zinc-100/80 ${glowPurple}`}
      >
        <img
          src={vectorHqShowcaseUrl}
          alt="Vector, your execution manager"
          className="relative z-10 mx-auto w-full max-h-[min(48vh,19rem)] object-contain object-center px-4 pb-3 pt-8 sm:max-h-80 sm:px-5 sm:pt-9 lg:max-h-[26rem] lg:px-6 lg:pb-4 lg:pt-8 xl:max-h-[27rem]"
          decoding="async"
        />
      </div>
      <div className="mt-4 text-center sm:mt-5">
        <p
          className={`text-xs font-semibold uppercase tracking-[0.12em] sm:text-[13px] sm:tracking-[0.13em] ${landingAccentText}`}
        >
          Vector
        </p>
        <p className="mt-1 text-xs font-medium leading-snug text-zinc-600 sm:text-sm">Your execution manager</p>
      </div>
    </div>
  );
}

function MeetVectorAgentSection() {
  const points = ["What's happening", "What's at risk", "What should leaders do next"];
  return (
    <SectionShell id="meet-vector-agent" divider className={sectionPad}>
      <ScrollFade>
        <div className="grid gap-12 lg:grid-cols-2 lg:items-start lg:gap-14">
          <div className="min-w-0 lg:pl-2">
            <header className={sectionHeaderClass}>
              <h2 className={`${sectionTitleClass} max-w-4xl`}>
                Meet <span className={landingTitleKeywordGradient}>Vector</span>
              </h2>
              <div className="mt-6 max-w-2xl space-y-6">
                <p className="text-pretty text-lg font-bold leading-snug text-zinc-950 sm:text-xl">
                  Not a SaaS. Not a Dashboard.
                </p>
                <p className={sectionProseMuted}>
                  Vector is on your team, it lives inside your existing tools and adapts to your company&apos;s
                  processes and routine.
                </p>
              </div>
            </header>
            <p className={`mt-10 sm:mt-12 ${sectionProseBody}`}>Vector always knows:</p>
            <ul className={`mt-3 space-y-3 sm:mt-4 ${sectionListEmphasis}`}>
              {points.map((x) => (
                <li key={x} className="flex items-start gap-3">
                  <span
                    className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border border-zinc-200/80 bg-zinc-50 text-xs text-zinc-500"
                    aria-hidden
                  >
                    ✓
                  </span>
                  <span>{x}</span>
                </li>
              ))}
            </ul>
            <div className="mt-8 sm:mt-10">
              <Link
                to="/signup"
                className="inline-flex items-center justify-center rounded-full bg-[#0F0F12] px-9 py-4 text-base font-semibold text-white no-underline shadow-[0_8px_24px_-12px_rgba(15,23,42,0.35)] transition-[transform,box-shadow] hover:scale-[1.02] hover:shadow-[0_12px_32px_-12px_rgba(15,23,42,0.2)]"
              >
                Meet Vector
              </Link>
            </div>
          </div>
          <div className="relative min-h-0 min-w-0 lg:pt-0">
            <MeetVectorAvatarShowcase />
          </div>
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

/* The questions Vector answers for you */
const THREE_PILLARS: {
  n: string;
  title: string;
  lead: string;
  examples: string[];
}[] = [
  {
    n: "1",
    title: "What's happening?",
    lead: "One current view of how work is moving, without a scavenger hunt.",
    examples: ["Issues & PRs", "Dependencies", "Execution rhythm"],
  },
  {
    n: "2",
    title: "What's at risk?",
    lead: "Drift and blockers surface early, while you can still act.",
    examples: ["Stalled work", "Hidden dependencies", "Slip risk"],
  },
  {
    n: "3",
    title: "What should leaders do next?",
    lead: "Concrete next moves, not another chart to decode.",
    examples: ["Escalate blockers", "Move capacity", "Re-prioritize with evidence"],
  },
];

function WhatVectorKnowsSection() {
  return (
    <SectionShell id="what-vector-knows" divider className={sectionPad}>
      <ScrollFade>
        <header className={sectionHeaderClass}>
          <h2 className={`${sectionTitleClass} max-w-none md:whitespace-nowrap`}>
            The questions <span className={landingAccentText}>Vector</span>{" "}
            <span className={titleAccent.threeThings}>answers for you</span>
          </h2>
        </header>
        <div className="mt-12 grid gap-6 lg:grid-cols-3 lg:gap-5">
          {THREE_PILLARS.map((p) => (
            <div
              key={p.title}
              className={`${panel} flex flex-col p-6 transition-transform duration-300 hover:-translate-y-0.5 hover:shadow-[0_16px_48px_-28px_rgba(232,120,190,0.14)]`}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0F0F12] text-sm font-bold text-white">
                {p.n}
              </span>
              <h3 className={`mt-3 ${cardTitleClass}`}>{p.title}</h3>
              <p className={`mt-2 text-base font-medium leading-snug text-zinc-700 sm:text-lg`}>{p.lead}</p>
              <ul className="mt-4 space-y-1.5 border-t border-zinc-200/70 pt-3 text-sm font-medium leading-snug text-zinc-600 sm:text-base">
                {p.examples.map((ex) => (
                  <li key={ex} className="flex gap-2">
                    <span className={landingAccentText} aria-hidden>
                      ·
                    </span>
                    <span>{ex}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

/* -- How Vector fits in your stack -- */
function StackSection() {
  return (
    <SectionShell id="stack" divider className={sectionPad}>
      <ScrollFade>
        <header className={sectionHeaderClass}>
          <h2 className={`${sectionTitleClass} max-w-4xl`}>
            Vector fits into your <span className={landingTitleKeywordGradient}>stack</span>
          </h2>
        </header>
        <div className="mt-12 grid items-center gap-12 lg:grid-cols-12 lg:gap-10 lg:pl-2">
          <div className="max-w-xl lg:col-span-5">
            <p className={sectionProseMuted}>
              Slack, GitHub, Linear, Notion, Jira, and internal tools all emit signals about execution.
            </p>
            <p className={`mt-4 ${sectionProseBody}`}>
              They flow into Vector&apos;s brain, and he produces{" "}
              <span className={landingTitleKeywordGradient}>insights, reports, and recommendations</span> leaders can
              act on.
            </p>
          </div>
          <div className="relative lg:col-span-7 lg:-mr-2 xl:-mr-4">
            <div className="relative">
              <PipelineProductVisual size="full" />
            </div>
          </div>
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

function PersonaLabelIcon({ kind }: { kind: "executives" | "leaders" | "teams" }) {
  const cls = "h-4 w-4 shrink-0 opacity-90";
  if (kind === "executives") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
        <circle cx="12" cy="12" r="2.25" strokeLinecap="round" />
        <path
          d="M12 4.5v2.25M12 17.25V21M4.5 12h2.25M17.25 12H21M6.22 6.22l1.59 1.59M16.19 16.19l1.59 1.59M6.22 17.78l1.59-1.59M16.19 7.81l1.59-1.59"
          strokeLinecap="round"
        />
        <circle cx="12" cy="12" r="8.25" strokeDasharray="3 3" strokeLinecap="round" />
      </svg>
    );
  }
  if (kind === "leaders") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
        <circle cx="12" cy="6" r="2" />
        <circle cx="6" cy="17" r="2" />
        <circle cx="18" cy="17" r="2" />
        <path d="M12 8v2.5M12 10.5c-2.2 0-4.1 1.2-5.1 3M12 10.5c2.2 0 4.1 1.2 5.1 3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
      <path
        d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PersonaWinLine({ line, highlight }: { line: string; highlight?: string }) {
  if (!highlight || !line.includes(highlight)) {
    return <>{line}</>;
  }
  const i = line.indexOf(highlight);
  return (
    <>
      {line.slice(0, i)}
      <span className={landingTitleKeywordGradient}>{highlight}</span>
      {line.slice(i + highlight.length)}
    </>
  );
}

/* Persona cards: payoff by audience */
function WhoSection() {
  const personas: {
    label: string;
    hook: string;
    wins: { line: string; highlight?: string }[];
    iconKind: "executives" | "leaders" | "teams";
  }[] = [
    {
      label: "Executives",
      hook: "Run execution with clarity",
      wins: [
        { line: "Spot risks early while there is still time to act" },
        { line: "Make decisions from real execution signals", highlight: "execution signals" },
        { line: "See how the organization is delivering in real time" },
      ],
      iconKind: "executives",
    },
    {
      label: "Engineering & product leaders",
      hook: "Scale how you run teams",
      wins: [
        { line: "Save hours every week chasing updates" },
        { line: "Detect work drift before it turns into delays", highlight: "work drift" },
        { line: "Spend more time coaching and unblocking teams" },
      ],
      iconKind: "leaders",
    },
    {
      label: "Teams",
      hook: "Ship work without meeting fatigue",
      wins: [
        { line: "Reduce “where are we” interruptions", highlight: "“where are we”" },
        { line: "Get clear visibility without constant check-ins" },
        { line: "Surface blockers as they happen and resolve them faster" },
      ],
      iconKind: "teams",
    },
  ];
  return (
    <SectionShell id="who" className={sectionPad}>
      <ScrollFade>
        <header className={sectionHeaderClass}>
          <h2 className={`${sectionTitleClass} max-w-none lg:whitespace-nowrap`}>
            An <span className={landingTitleKeywordGradient}>AI manager</span> that works for everyone
          </h2>
        </header>

        <div className="mt-12 grid gap-5 sm:gap-6 lg:grid-cols-3 lg:gap-8">
          {personas.map((p) => (
            <article
              key={p.label}
              className="group flex h-full flex-col overflow-hidden rounded-3xl border border-zinc-200/80 bg-white/90 shadow-[0_20px_50px_-32px_rgba(15,23,42,0.12)] backdrop-blur-sm transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_56px_-36px_rgba(15,23,42,0.14)]"
            >
              <div className="h-1.5 w-full bg-zinc-900" aria-hidden />
              <div className="flex flex-1 flex-col px-6 pb-7 pt-6 sm:px-7 sm:pt-7">
                <div className="flex items-center gap-2.5 text-zinc-600">
                  <PersonaLabelIcon kind={p.iconKind} />
                  <p
                    className={`text-xs font-semibold uppercase tracking-[0.11em] sm:text-[13px] sm:tracking-[0.13em] ${landingTitleKeywordGradient}`}
                  >
                    {p.label}
                  </p>
                </div>
                <h3 className="mt-1.5 text-[1.35rem] font-bold leading-snug tracking-tight text-zinc-900 sm:mt-2 sm:text-2xl sm:leading-tight">
                  {p.hook}
                </h3>
                <ul className="mt-6 flex flex-1 flex-col gap-3" role="list">
                  {p.wins.map((w) => (
                    <li
                      key={w.line}
                      className="flex items-start gap-3 rounded-2xl bg-zinc-50/80 px-3.5 py-2.5 text-sm leading-snug text-zinc-600 ring-1 ring-zinc-100/90 sm:text-[15px]"
                    >
                      <span
                        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-zinc-200/80 bg-zinc-50 text-[10px] font-bold text-zinc-500"
                        aria-hidden
                      >
                        ✓
                      </span>
                      <span className="min-w-0">
                        <PersonaWinLine line={w.line} highlight={w.highlight} />
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

/* -- CTA + Footer -- */
function CtaSection() {
  return (
    <SectionShell id="cta" divider className={sectionPad}>
      <ScrollFade>
        <div className="relative overflow-hidden rounded-3xl border border-zinc-200/70 bg-white px-6 py-14 text-left shadow-[0_20px_50px_-36px_rgba(15,23,42,0.08)] sm:px-12 sm:py-16">
        <div className="relative">
          <h2 className={`${sectionTitleClass} max-w-4xl`}>
            <span className="block">
              Less time collecting <span className={landingTitleKeywordGradient}>signals</span>.
            </span>
            <span className="block mt-1 sm:mt-0">
              More time on <span className={landingTitleKeywordGradient}>strategy</span>.
            </span>
          </h2>
          <p className={`mt-4 max-w-md ${sectionCtaMuted}`}>Setup takes minutes.</p>
          <ol className={`mt-8 flex max-w-md flex-col gap-4 ${sectionCtaList}`}>
            <li className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#0F0F12] text-xs font-bold text-white">1</span>
              Connect tools
            </li>
            <li className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#0F0F12] text-xs font-bold text-white">2</span>
              <span>Vector analyzes execution signals from your stack.</span>
            </li>
            <li className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#0F0F12] text-xs font-bold text-white">3</span>
              <span>Vector is ready to work.</span>
            </li>
          </ol>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link
              to="/signup"
              className="inline-flex items-center justify-center rounded-full bg-[#0F0F12] px-8 py-3.5 text-sm font-semibold text-white no-underline shadow-[0_8px_24px_-12px_rgba(15,23,42,0.35)] transition-transform hover:scale-[1.02]"
            >
              Meet Vector
            </Link>
            <a
              href="https://calendar.app.google/1kwPDrjBZxVVaBAL6"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-full border border-zinc-200/90 bg-white/90 px-8 py-3.5 text-sm font-semibold text-zinc-800 no-underline backdrop-blur-sm transition-colors hover:border-zinc-300"
            >
              Book demo
            </a>
          </div>
        </div>
        </div>
      </ScrollFade>
    </SectionShell>
  );
}

function LandingFooter() {
  return (
    <footer className="border-t border-zinc-200/50 bg-white/30 backdrop-blur-sm">
      <div className="mx-auto max-w-[96rem] px-5 py-10 sm:px-8">
        <p className="text-center text-xs text-zinc-400">© 2026 Vector</p>
      </div>
    </footer>
  );
}

export function LandingBelowHero() {
  return (
    <>
      <WhoSection />
      {showProblemSection ? <ProblemSection /> : null}
      <MeetVectorAgentSection />
      {showWhatVectorKnowsSection ? <WhatVectorKnowsSection /> : null}
      <StackSection />
      <CoreFeaturesSection />
      {showHowVectorReconstructsSection ? <HowVectorReconstructsSection /> : null}
      <CtaSection />
      <LandingFooter />
    </>
  );
}
