import { Link, useParams } from "react-router-dom";

import { getAdminPassword } from "../lib/adminCredentials";
import { adminCanonicalClient } from "../lib/canonicalApi";
import CanonicalDebugPage from "../pages/debug/CanonicalDebugPage";
import AdminTenantStep1 from "./AdminTenantStep1";
import AdminTenantStep2 from "./AdminTenantStep2";
import { OperatorIntro, OperatorSection } from "./ui/OperatorSections";
import { CollapsibleDebug } from "./ui/OperatorSections";

export default function AdminTenantDebugPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const pw = getAdminPassword();

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }
  if (!pw) {
    return <p className="text-sm text-red-700">Admin session missing.</p>;
  }

  return (
    <div className="space-y-8">
      <OperatorIntro title="Debug">
        Low-level tables and identifiers for engineers. Collapse sections when you only need the
        operator views elsewhere in this workspace.
      </OperatorIntro>

      <OperatorSection title="Quick links" description="Return to operator-focused pages.">
        <p className="text-sm text-stone-600">
          Workspace summary and health live under{" "}
          <Link to={`/admin/tenants/${tenantId}/workspace`} className="text-blue-700 underline">
            Workspace
          </Link>
          ; the execution graph UI under{" "}
          <Link
            to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph`}
            className="text-blue-700 underline"
          >
            Execution graph
          </Link>
          .
        </p>
      </OperatorSection>

      <CollapsibleDebug title="Raw ingestion records (Step 1)" defaultOpen>
        <AdminTenantStep1 />
      </CollapsibleDebug>

      <CollapsibleDebug title="Projection rows (Step 2)" defaultOpen>
        <AdminTenantStep2 />
      </CollapsibleDebug>

      <CollapsibleDebug title="Canonical — work objects, people, relationships, external refs, graph, pipeline status" defaultOpen>
        <CanonicalDebugPage
          client={adminCanonicalClient(tenantId, pw)}
          entityBasePath={`/admin/tenants/${tenantId}/data-pipeline/execution-graph`}
          dashboardHref="/admin"
          visualTheme="admin"
          secondaryNavHref={`/admin/tenants/${tenantId}/data-pipeline`}
          secondaryNavLabel="Data pipeline"
        />
      </CollapsibleDebug>
    </div>
  );
}
