import { useParams } from "react-router-dom";

import { getAdminPassword } from "../lib/adminCredentials";
import { adminCanonicalClient } from "../lib/canonicalApi";
import CanonicalDebugPage from "../pages/debug/CanonicalDebugPage";
import Step3CanonicalResetPanel from "./Step3CanonicalResetPanel";

const EXECUTION_GRAPH_TABS = ["actors", "artifacts", "relationships", "graph", "status"] as const;

export default function AdminExecutionGraphPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const pw = getAdminPassword();

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (!pw) {
    return <p className="text-sm text-red-700">Admin session missing.</p>;
  }

  const base = `/admin/tenants/${tenantId}/data-pipeline/execution-graph`;

  return (
    <div>
      <Step3CanonicalResetPanel tenantId={tenantId} />
      <CanonicalDebugPage
        client={adminCanonicalClient(tenantId, pw)}
        entityBasePath={base}
        dashboardHref="/admin"
        visualTheme="admin"
        visibleTabIds={EXECUTION_GRAPH_TABS}
        tabLabelOverrides={{
          artifacts: "Work objects",
          actors: "People",
          relationships: "Relationships",
          graph: "Graph",
          status: "Pipeline status",
        }}
        operatorChrome
        tertiaryNavHref={`/admin/tenants/${tenantId}/data-pipeline/debug`}
        tertiaryNavLabel="Full debug"
      />
    </div>
  );
}
