import {
  marketingBody,
  marketingSectionTitle,
  workspaceAppPageMain,
  workspaceAppPageSection,
} from "../../components/marketing/marketingStyles";
import WorkspaceManagersTab from "../../components/workspace/WorkspaceManagersTab";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

export default function AppTeamsPage() {
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);

  if (me.isPending || !me.data) {
    return (
      <main
        className={`${workspaceAppPageMain} flex flex-col items-center justify-center py-16 sm:py-20`}
      >
        <div
          className="h-9 w-9 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
        <p className={`${marketingBody} mt-4 text-center text-sm text-zinc-600`}>Loading teams…</p>
      </main>
    );
  }

  const companyLabel = me.data.company_name?.trim() ? me.data.company_name : "Your company";

  return (
    <main className={workspaceAppPageMain}>
      <section className={workspaceAppPageSection}>
        <header>
          <h1 className={marketingSectionTitle}>
            Workspace ({companyLabel}) · Teams
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-zinc-500 sm:text-base">
            Build teams from your Slack roster—names and members save for everyone here.
          </p>
        </header>

        <div className="mt-6 lg:mt-8">
          <WorkspaceManagersTab />
        </div>
      </section>
    </main>
  );
}
