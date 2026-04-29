import { marketingBody, marketingSectionTitle, workspaceFlatPanel } from "../../components/marketing/marketingStyles";
import WorkspaceManagersTab from "../../components/workspace/WorkspaceManagersTab";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

export default function AppTeamsPage() {
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);

  if (me.isPending || !me.data) {
    return (
      <main className="relative mx-auto flex w-full max-w-[min(100%,96rem)] flex-col items-center justify-center px-6 py-16 sm:px-10 lg:px-12">
        <div
          className="h-9 w-9 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
        <p className={`${marketingBody} mt-5 text-center text-zinc-600`}>Loading teams…</p>
      </main>
    );
  }

  const companyLabel = me.data.company_name?.trim() ? me.data.company_name : "Your company";

  return (
    <main className="relative mx-auto w-full max-w-[min(100%,96rem)] px-6 py-10 pb-16 sm:px-10 sm:py-12 lg:px-12 lg:py-14">
      <section className={`${workspaceFlatPanel} px-8 py-9 sm:px-10 sm:py-10 lg:px-12 lg:py-11`}>
        <h1 className={marketingSectionTitle}>
          Workspace ({companyLabel}) · Teams
        </h1>
        <p className={`${marketingBody} mt-3 max-w-2xl text-zinc-600`}>
          Name teams and assign people from Slack. Saved for everyone in this workspace.
        </p>

        <div className="mt-10 lg:mt-12">
          <WorkspaceManagersTab />
        </div>
      </section>
    </main>
  );
}
