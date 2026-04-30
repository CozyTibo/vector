import {
  marketingBody,
  workspaceAppBreadcrumbCurrentLink,
  workspaceAppBreadcrumbProduct,
  workspaceAppBreadcrumbSep,
  workspaceAppPageHeader,
  workspaceAppPageMain,
} from "../../components/marketing/marketingStyles";
import { workspaceSpinnerHero } from "../../components/workspace/workspaceUiTokens";
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
        <div className={workspaceSpinnerHero} aria-hidden />
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

      <div className="mt-4 lg:mt-6">
        <WorkspaceManagersTab />
      </div>
    </main>
  );
}
