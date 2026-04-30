import {
  marketingBody,
  workspaceAppBreadcrumbCurrentLink,
  workspaceAppBreadcrumbProduct,
  workspaceAppBreadcrumbSep,
  workspaceAppPageHeader,
  workspaceAppPageMain,
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

  return (
    <main className={workspaceAppPageMain}>
      <header className={workspaceAppPageHeader}>
        <nav aria-label="Breadcrumb">
          <h1 className="flex min-w-0 flex-nowrap items-baseline justify-start gap-x-1 leading-none">
            <span className={workspaceAppBreadcrumbProduct}>Vector</span>
            <span className={workspaceAppBreadcrumbSep} aria-hidden="true">
              /
            </span>
            <a
              href="#"
              className={workspaceAppBreadcrumbCurrentLink}
              aria-current="page"
              onClick={(e) => {
                e.preventDefault();
              }}
            >
              Teams
            </a>
          </h1>
        </nav>
      </header>

      <p className="max-w-2xl text-sm leading-snug text-zinc-500 sm:text-base sm:leading-snug">
        Build teams from your Slack roster—names and members save for everyone here.
      </p>

      <div className="mt-4 lg:mt-6">
        <WorkspaceManagersTab />
      </div>
    </main>
  );
}
