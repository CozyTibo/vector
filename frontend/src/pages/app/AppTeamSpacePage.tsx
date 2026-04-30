import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import {
  marketingBody,
  workspaceAppBreadcrumbAncestorLink,
  workspaceAppBreadcrumbSep,
  workspaceAppPageMain,
  workspaceFlatPanel,
} from "../../components/marketing/marketingStyles";
import SlackUserAvatar from "../../components/workspace/SlackUserAvatar";
import { workspaceSpinnerHero } from "../../components/workspace/workspaceUiTokens";
import { fetchOnboarding, fetchSlackWorkspaceMembers, type SlackWorkspaceMember } from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";
import {
  defaultTeamsFromOnboarding,
  membersOrderedWithManagerFirst,
} from "../../lib/workspaceManagerTeams";

const membersSectionLabelClass = "text-sm font-semibold text-zinc-600";

function Toggle({
  checked,
  onChange,
  label,
  disabled = false,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled}
      disabled={disabled}
      aria-label={label}
      onClick={() => {
        if (!disabled) onChange(!checked);
      }}
      className={`relative inline-flex h-7 w-[2.875rem] shrink-0 items-center justify-start rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? "bg-[color:var(--color-action-primary)]" : "bg-zinc-200"
      }`}
    >
      <span
        className={`inline-block h-6 w-6 rounded-full bg-white shadow-sm transition-transform ${
          checked ? "translate-x-[1.125rem]" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

function SectionTitle({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <h2 className={`text-base font-semibold tracking-tight text-zinc-900 ${className}`}>{children}</h2>;
}

/** Grouped settings — same quiet panel frame as Signals / Teams */
function SettingsColumnGroup({ title, children }: { title: string; children: ReactNode }) {
  const headingId = `settings-group-${title.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <section className={`${workspaceFlatPanel} scroll-mt-4 p-6 sm:p-8`} aria-labelledby={headingId}>
      <div id={headingId} className="border-b border-zinc-100 pb-4">
        <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-500">{title}</p>
      </div>
      <div className="flex flex-col gap-14 pt-6 sm:gap-16 sm:pt-8">{children}</div>
    </section>
  );
}

/** Compact label — value rows (no rigid grid) */
function ConfigRows({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <ul className="space-y-2.5">
      {rows.map((row) => (
        <li key={row.label} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm leading-snug">
          <span className="text-zinc-500">{row.label}</span>
          <span className="select-none text-zinc-300">·</span>
          <span className="font-medium text-zinc-900">{row.value}</span>
        </li>
      ))}
    </ul>
  );
}

function SettingBlock({
  title,
  description,
  enabled,
  onToggle,
  children,
  toggleDisabled = false,
}: {
  title: string;
  description?: string;
  enabled: boolean;
  onToggle: (next: boolean) => void;
  children: ReactNode;
  /** When set, switch is off and cannot be turned on (e.g. coming soon). */
  toggleDisabled?: boolean;
}) {
  const titleActive = enabled || toggleDisabled;
  const dimBody = !enabled && !toggleDisabled;
  return (
    <div>
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <h3
            className={`text-[15px] font-semibold tracking-tight sm:text-base ${titleActive ? "text-zinc-950" : "text-zinc-400"}`}
          >
            {title}
          </h3>
          {description ? (
            <p className="mt-2 max-w-xl text-xs leading-relaxed text-zinc-500 sm:text-[13px]">{description}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2 pt-0.5">
          <span
            className={`text-xs font-medium tabular-nums ${enabled ? "text-zinc-600" : "text-zinc-400"}`}
            aria-hidden
          >
            {enabled ? "On" : "Off"}
          </span>
          <Toggle
            checked={enabled}
            onChange={onToggle}
            disabled={toggleDisabled}
            label={`${title} ${enabled ? "enabled" : "disabled"}`}
          />
        </div>
      </div>
      <div className={`mt-5 transition-opacity ${dimBody ? "opacity-[0.38]" : "opacity-100"}`}>{children}</div>
    </div>
  );
}

export default function AppTeamSpacePage() {
  const { teamId } = useParams<{ teamId: string }>();
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);
  const tenantId = me.data?.tenant_id;

  const [managerInsightsOn, setManagerInsightsOn] = useState(true);

  const ob = useQuery({
    queryKey: ["onboarding", apiBase, tenantId ?? ""],
    queryFn: () => fetchOnboarding(apiBase),
    enabled: Boolean(tenantId),
  });

  const slackMembers = useQuery({
    queryKey: ["slack-workspace-members-workspace-page", apiBase, tenantId ?? ""],
    queryFn: () => fetchSlackWorkspaceMembers(apiBase),
    enabled: Boolean(tenantId) && Boolean(ob.data?.slack_connected),
    retry: false,
  });

  const slackRoster = slackMembers.data ?? [];
  const rosterById = useMemo(() => {
    const m = new Map<string, SlackWorkspaceMember>();
    for (const u of slackRoster) {
      m.set(u.id, u);
    }
    return m;
  }, [slackRoster]);

  if (me.isPending || !me.data) {
    return (
      <main className={`${workspaceAppPageMain} flex flex-col items-center justify-center py-16 sm:py-20`}>
        <div className={workspaceSpinnerHero} aria-hidden />
        <p className={`${marketingBody} mt-4 text-center text-sm text-zinc-600`}>Loading team…</p>
      </main>
    );
  }

  if (ob.isPending || !ob.data) {
    return (
      <main className={`${workspaceAppPageMain} flex flex-col items-center justify-center py-16 sm:py-20`}>
        <div className={workspaceSpinnerHero} aria-hidden />
        <p className={`${marketingBody} mt-4 text-center text-sm text-zinc-600`}>Loading team…</p>
      </main>
    );
  }

  if (ob.isError) {
    return (
      <main className={workspaceAppPageMain}>
        <p className={`${marketingBody} text-base text-red-700`}>Could not load workspace teams.</p>
      </main>
    );
  }

  const teams = defaultTeamsFromOnboarding(ob.data.answers);
  const team = teamId ? teams.find((t) => t.id === teamId) : undefined;

  if (!team) {
    return <Navigate to="/app/teams" replace />;
  }

  const displayName = team.name.trim() || "Team";

  return (
    <main className={`${workspaceAppPageMain} space-y-10 lg:space-y-12`}>
      <header className="space-y-4">
        <nav aria-label="Breadcrumb">
          <p className="flex min-w-0 flex-nowrap items-baseline gap-x-1 text-sm leading-none text-zinc-500">
            <span className="shrink-0 font-normal">Vector</span>
            <span className={workspaceAppBreadcrumbSep} aria-hidden="true">
              /
            </span>
            <Link to="/app/teams" className={workspaceAppBreadcrumbAncestorLink}>
              Teams
            </Link>
            <span className={workspaceAppBreadcrumbSep} aria-hidden="true">
              /
            </span>
            <span className="min-w-0 truncate font-normal text-zinc-900" aria-current="page">
              {displayName}
            </span>
          </p>
        </nav>

        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">{displayName} space</h1>
          <p className="mt-2 max-w-2xl text-base leading-snug text-zinc-500">
            Define how Vector operates with your team.
          </p>
        </div>
      </header>

      {/* Primary two-column operational layout */}
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-10 lg:gap-12 xl:gap-16">
        {/* LEFT ~70% */}
        <div className="lg:col-span-7">
          <div className="flex flex-col gap-6 lg:gap-8">
            <SettingsColumnGroup title="Reporting">
              <SettingBlock
                title="Manager insights"
                description="Focused digests for leads—signals and context without the full team report."
                enabled={managerInsightsOn}
                onToggle={setManagerInsightsOn}
              >
                <ConfigRows
                  rows={[
                    { label: "Where insights go", value: "Slack" },
                    { label: "Frequency", value: "Weekly" },
                  ]}
                />
              </SettingBlock>

              <SettingBlock
                title="Reports"
                description="Scheduled summaries to Slack so managers stay oriented without digging through threads."
                enabled={false}
                onToggle={() => {}}
                toggleDisabled
              >
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-400">Coming soon</p>
              </SettingBlock>
            </SettingsColumnGroup>

            <SettingsColumnGroup title="Execution">
              <SettingBlock
                title="Daily check-ins"
                description="Vector prompts the channel on a cadence so progress and blockers stay visible."
                enabled={false}
                onToggle={() => {}}
                toggleDisabled
              >
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-400">Coming soon</p>
              </SettingBlock>

              <SettingBlock
                title="Peer reviews"
                description="Lightweight prompts so people reflect on execution, clarity, and ownership."
                enabled={false}
                onToggle={() => {}}
                toggleDisabled
              >
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-400">Coming soon</p>
              </SettingBlock>
            </SettingsColumnGroup>

            <SettingsColumnGroup title="Improvement">
              <SettingBlock
                title="Retrospectives"
                description="Structured look-backs on a fixed rhythm when you want deeper team learning."
                enabled={false}
                onToggle={() => {}}
                toggleDisabled
              >
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-400">Coming soon</p>
              </SettingBlock>
            </SettingsColumnGroup>
          </div>
        </div>

        {/* RIGHT ~30% */}
        <aside className="lg:col-span-3">
          <SectionTitle>Team members</SectionTitle>
          <div className="mt-4">
            <p className={membersSectionLabelClass}>Members</p>
            {slackMembers.isPending ? (
              <p className="mt-2 text-sm text-zinc-500">Loading Slack directory…</p>
            ) : team.members.length === 0 ? (
              <p className="mt-2 text-base text-zinc-500">None yet.</p>
            ) : (
              <ul className="mt-2 flex flex-col gap-2">
                {membersOrderedWithManagerFirst(team).map((m) => {
                  const rosterRow = rosterById.get(m.slack_user_id);
                  const avatarUrl = rosterRow?.image_48 ?? null;
                  const display = m.label.trim() || m.username;
                  const isManager =
                    team.manager_slack_user_id !== null &&
                    m.slack_user_id === team.manager_slack_user_id;
                  return (
                    <li
                      key={m.slack_user_id}
                      className="inline-flex w-full max-w-full items-center gap-2 rounded-lg bg-zinc-100 py-1.5 pl-1.5 pr-1.5 text-zinc-900"
                    >
                      <SlackUserAvatar imageUrl={avatarUrl} name={display} size="md" />
                      <span className="min-w-0 truncate text-base font-medium text-[#0F0F12]">{m.label}</span>
                      <span className="shrink-0 text-sm text-zinc-500">@{m.username}</span>
                      {isManager ? (
                        <span className="shrink-0 rounded-sm bg-zinc-200/55 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600 sm:text-[11px]">
                          Manager
                        </span>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
