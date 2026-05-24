import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../cortex/SectionSkeleton";
import { DeployInfoFooter } from "./DeployInfoFooter";
import { OperatorCompactActions } from "./OperatorCompactActions";
import { OperatorConnectorsTable } from "./OperatorConnectorsTable";
import { OperatorContinuityFactsSection } from "./OperatorContinuityFactsSection";
import { OperatorRecentEventsSection } from "./OperatorRecentEventsSection";
import { OperatorStatusBannerSection } from "./OperatorStatusBannerSection";
import { useOperatorOverview } from "./useOperatorOverview";

export default function OperatorOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const overviewQ = useOperatorOverview();

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  if (overviewQ.isError) {
    const msg = (overviewQ.error as Error).message;
    if (msg === "operator_admin_v2_disabled") {
      return (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-950">
          Operator v2 is enabled in the UI but disabled on the API (CORTEX_ADMIN_V2). Enable the backend flag or
          turn off VITE_CORTEX_ADMIN_V2.
        </section>
      );
    }
    return <p className="text-sm text-red-700">{msg}</p>;
  }

  const data = overviewQ.data;
  const loading = overviewQ.isPending && !data;

  return (
    <div className="space-y-6">
      {loading ? (
        <SectionSkeleton variant="strip" />
      ) : data ? (
        <OperatorStatusBannerSection banner={data.status_banner} tenantId={tenantId} />
      ) : null}

      {loading ? (
        <SectionSkeleton variant="attention" />
      ) : data ? (
        <OperatorContinuityFactsSection facts={data.continuity_facts} tenantId={tenantId} />
      ) : null}

      {loading ? (
        <SectionSkeleton variant="table" />
      ) : data ? (
        <OperatorRecentEventsSection events={data.recent_events} tenantId={tenantId} />
      ) : null}

      {loading ? (
        <SectionSkeleton variant="actions" />
      ) : data ? (
        <OperatorCompactActions runnableConnectors={data.runnable_connectors} />
      ) : null}

      <OperatorConnectorsTable connectors={data?.connectors ?? []} loading={loading} />

      {data?.scheduler ? (
        <section className="rounded-xl border border-stone-200 bg-white p-4 text-sm text-stone-700 shadow-sm">
          <span className="font-medium">{data.scheduler.operator_mode_label ?? "Scheduler"}</span>
          <span className="text-stone-500">
            {" "}
            · beat {data.scheduler.beat_interval_seconds}s · gap {data.scheduler.min_gap_seconds}s
          </span>
          <Link
            to={`/admin/tenants/${tenantId}/cortex/settings`}
            className="ml-3 text-sm font-medium text-indigo-700 no-underline hover:underline"
          >
            Settings
          </Link>
        </section>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
