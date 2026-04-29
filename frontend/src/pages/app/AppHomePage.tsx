import {
  marketingBody,
  marketingSectionTitle,
  workspaceAppPageMain,
  workspaceAppPageSection,
} from "../../components/marketing/marketingStyles";
import { currentCoveragePresentation } from "../../components/workspace/signalCoverageCopy";
import { signalStrengthPercentLive } from "../../components/workspace/signalCatalog";
import WorkspaceSignalsTab from "../../components/workspace/WorkspaceSignalsTab";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

export default function AppHomePage() {
  const apiBase = productApiBase();
  const me = useProductMeQuery(apiBase);

  if (me.isPending || !me.data) {
    return (
      <main className="relative mx-auto flex w-full max-w-[min(100%,96rem)] flex-col items-center justify-center px-6 py-16 sm:px-10 lg:px-12">
        <div
          className="h-9 w-9 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
          aria-hidden
        />
        <p className={`${marketingBody} mt-5 text-center text-zinc-600`}>Loading your workspace…</p>
      </main>
    );
  }

  const { company_name, use_mock_connectors, connected_connectors } = me.data;
  const companyLabel = company_name?.trim() ? company_name : "Your company";
  const pctLive = signalStrengthPercentLive(
    new Set((connected_connectors ?? []).map((c) => c.toLowerCase())),
  );
  const coverageHero = currentCoveragePresentation(pctLive);

  return (
    <main className={workspaceAppPageMain}>
      <section className={workspaceAppPageSection}>
        <h1 className={marketingSectionTitle}>
          Workspace ({companyLabel}) · Signals
        </h1>
        <p className={`mt-3 max-w-2xl text-base leading-relaxed sm:text-lg ${coverageHero.toneClass}`}>
          {coverageHero.headlineSentence}
        </p>

        <div className="mt-6 lg:mt-8">
          <WorkspaceSignalsTab
            connectedConnectors={connected_connectors ?? []}
            useMockConnectors={Boolean(use_mock_connectors)}
          />
        </div>
      </section>
    </main>
  );
}
