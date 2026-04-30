import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useParams } from "react-router-dom";

import {
  marketingBody,
  workspaceAppBreadcrumbAncestorLink,
  workspaceAppBreadcrumbSep,
  workspaceAppPageHeader,
  workspaceAppPageMain,
} from "../../components/marketing/marketingStyles";
import { workspaceSpinnerHero } from "../../components/workspace/workspaceUiTokens";
import { fetchOnboarding } from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";
import { defaultTeamsFromOnboarding } from "../../lib/workspaceManagerTeams";

export default function AppTeamSpacePage() {
  const { teamId } = useParams<{ teamId: string }>();
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);
  const tenantId = me.data?.tenant_id;

  const ob = useQuery({
    queryKey: ["onboarding", apiBase, tenantId ?? ""],
    queryFn: () => fetchOnboarding(apiBase),
    enabled: Boolean(tenantId),
  });

  if (me.isPending || !me.data) {
    return (
      <main
        className={`${workspaceAppPageMain} flex flex-col items-center justify-center py-16 sm:py-20`}
      >
        <div className={workspaceSpinnerHero} aria-hidden />
        <p className={`${marketingBody} mt-4 text-center text-sm text-zinc-600`}>Loading team…</p>
      </main>
    );
  }

  if (ob.isPending || !ob.data) {
    return (
      <main
        className={`${workspaceAppPageMain} flex flex-col items-center justify-center py-16 sm:py-20`}
      >
        <div className={workspaceSpinnerHero} aria-hidden />
        <p className={`${marketingBody} mt-4 text-center text-sm text-zinc-600`}>Loading team…</p>
      </main>
    );
  }

  if (ob.isError) {
    return (
      <main className={workspaceAppPageMain}>
        <p className={`${marketingBody} text-base text-rose-700`}>Could not load workspace teams.</p>
      </main>
    );
  }

  const teams = defaultTeamsFromOnboarding(ob.data.answers);
  const team = teamId ? teams.find((t) => t.id === teamId) : undefined;

  if (!team) {
    return <Navigate to="/app/teams" replace />;
  }

  const companyName = me.data.company_name.trim() || "Workspace";

  return (
    <main className={workspaceAppPageMain}>
      <header className={workspaceAppPageHeader}>
        <nav aria-label="Breadcrumb">
          <h1 className="flex min-w-0 flex-nowrap items-baseline justify-start gap-x-1 leading-none">
            <span className="min-w-0 max-w-[42%] shrink truncate text-sm font-normal text-zinc-500 sm:max-w-[min(100%,20rem)]">
              {companyName}
            </span>
            <span className={workspaceAppBreadcrumbSep} aria-hidden="true">
              /
            </span>
            <Link to="/app/teams" className={workspaceAppBreadcrumbAncestorLink}>
              Teams
            </Link>
            <span className={workspaceAppBreadcrumbSep} aria-hidden="true">
              /
            </span>
            <span
              className="min-w-0 max-w-[38%] shrink truncate text-sm font-normal text-zinc-900 sm:max-w-[min(100%,24rem)]"
              aria-current="page"
            >
              {team.name.trim() || "Team"}
            </span>
          </h1>
        </nav>
      </header>
    </main>
  );
}
