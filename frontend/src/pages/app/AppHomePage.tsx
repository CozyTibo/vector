import {
  marketingBody,
  workspaceAppBreadcrumbCurrentLink,
  workspaceAppBreadcrumbProduct,
  workspaceAppBreadcrumbSep,
  workspaceAppPageHeader,
  workspaceAppPageMain,
  workspaceAppShellMaxWidth,
} from "../../components/marketing/marketingStyles";
import WorkspaceSignalsTab from "../../components/workspace/WorkspaceSignalsTab";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

export default function AppHomePage() {
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);

  if (me.isPending || !me.data) {
    return (
      <main
        className={`relative mx-auto flex w-full ${workspaceAppShellMaxWidth} flex-col items-center justify-center px-6 py-16 sm:px-10 lg:px-12`}
      >
        <div
          className="h-9 w-9 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
        <p className={`${marketingBody} mt-5 text-center text-zinc-600`}>Loading your workspace…</p>
      </main>
    );
  }

  const { use_mock_connectors, connected_connectors } = me.data;

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
              Signals
            </a>
          </h1>
        </nav>
      </header>

      <WorkspaceSignalsTab
        connectedConnectors={connected_connectors ?? []}
        useMockConnectors={Boolean(use_mock_connectors)}
      />
    </main>
  );
}
