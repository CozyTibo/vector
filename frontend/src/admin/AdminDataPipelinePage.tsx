import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  adminCanonicalClient,
  fetchArtifactsPage,
  fetchCanonicalStatus,
  fetchGithubIngestionRuns,
} from "../lib/canonicalApi";
import { adminJson } from "../lib/adminFetch";
import { getAdminPassword } from "../lib/adminCredentials";
import AdminTenantStep1 from "./AdminTenantStep1";
import AdminTenantStep2 from "./AdminTenantStep2";
import { CollapsibleDebug, OperatorIntro, OperatorSection } from "./ui/OperatorSections";
import { StatusBadge } from "./ui/StatusBadge";

type Conn = { id: string; provider: string; status: string; created_at: string };

export default function AdminDataPipelinePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [sp] = useSearchParams();
  const focus = sp.get("focus");
  const pw = getAdminPassword();

  const connQ = useQuery({
    queryKey: ["admin-connections", tenantId],
    queryFn: () => adminJson<{ items: Conn[] }>(`/admin/tenants/${tenantId}/connections`),
    enabled: Boolean(tenantId),
  });

  const rawQ = useQuery({
    queryKey: ["admin-raw", tenantId, "pipeline"],
    queryFn: () =>
      adminJson<{ total: number; items: { fetched_at: string }[] }>(
        `/admin/tenants/${tenantId}/raw-ingestion?limit=1&offset=0`,
      ),
    enabled: Boolean(tenantId),
  });

  const ghConn = connQ.data?.items.find((c) => c.provider === "github");
  const linConn = connQ.data?.items.find((c) => c.provider === "linear");

  const ghProjQ = useQuery({
    queryKey: ["admin-projections-pipeline", tenantId, ghConn?.id],
    queryFn: () =>
      adminJson<{ total: number }>(
        `/admin/tenants/${tenantId}/projections/github/${ghConn!.id}/rows?entity=repositories&limit=1&offset=0`,
      ),
    enabled: Boolean(tenantId && ghConn?.id),
  });

  const linProjQ = useQuery({
    queryKey: ["admin-projections-pipeline-l", tenantId, linConn?.id],
    queryFn: () =>
      adminJson<{ total: number }>(
        `/admin/tenants/${tenantId}/projections/linear/${linConn!.id}/rows?entity=teams&limit=1&offset=0`,
      ),
    enabled: Boolean(tenantId && linConn?.id),
  });

  const runsQ = useQuery({
    queryKey: ["github-ingestion-runs", `admin:${tenantId}`, "pipeline"],
    queryFn: () => fetchGithubIngestionRuns(adminCanonicalClient(tenantId, pw!)),
    enabled: Boolean(tenantId && pw && ghConn),
  });

  const connId = runsQ.data?.items[0]?.connection_id ?? ghConn?.id ?? "";
  const canonCountQ = useQuery({
    queryKey: ["canonical-artifacts-count", tenantId, "pipe"],
    queryFn: () => fetchArtifactsPage(adminCanonicalClient(tenantId, pw!), { limit: 1, offset: 0 }),
    enabled: Boolean(tenantId && pw),
  });

  const statusQ = useQuery({
    queryKey: ["canonical-status-pipeline", tenantId, connId],
    queryFn: () => fetchCanonicalStatus(adminCanonicalClient(tenantId, pw!), connId, "github"),
    enabled: Boolean(tenantId && pw && connId),
  });

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant.</p>;
  }

  const rawTotal = rawQ.data?.total ?? 0;
  const lastRaw = rawQ.data?.items[0]?.fetched_at;
  const projTotal = (ghProjQ.data?.total ?? 0) + (linProjQ.data?.total ?? 0);
  const graphTotal = canonCountQ.data?.total ?? 0;
  const lag = statusQ.data?.step3_lag_rows;

  return (
    <div className="space-y-8">
      <OperatorIntro title="Data pipeline">
        Data moves in three stages: raw envelopes from APIs, normalized projection tables per connector,
        then the execution graph that powers product insights. Use this page to run syncs, reset layers,
        and open deep inspection when something looks wrong.
      </OperatorIntro>

      <OperatorSection
        title="Pipeline overview"
        description="High-level counts; exact numbers may span many entity types."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-stone-900">Raw ingestion</h3>
              <StatusBadge tone={rawTotal > 0 ? "ok" : "neutral"}>
                {rawTotal > 0 ? "Receiving data" : "Empty"}
              </StatusBadge>
            </div>
            <p className="mt-2 text-2xl font-semibold text-stone-900">{rawTotal.toLocaleString()}</p>
            <p className="text-sm text-stone-600">envelope(s) stored</p>
            <p className="mt-2 text-xs text-stone-500">
              Last envelope: {lastRaw ? new Date(lastRaw).toLocaleString() : "—"}
            </p>
          </div>
          <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-stone-900">Projections</h3>
              <StatusBadge tone={projTotal > 0 ? "ok" : "neutral"}>
                {projTotal > 0 ? "Populated" : "Waiting"}
              </StatusBadge>
            </div>
            <p className="mt-2 text-2xl font-semibold text-stone-900">{projTotal.toLocaleString()}</p>
            <p className="text-sm text-stone-600">rows (sample entities)</p>
          </div>
          <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-stone-900">Execution graph</h3>
              <StatusBadge tone={graphTotal > 0 ? "ok" : "neutral"}>
                {graphTotal > 0 ? "Active" : "Empty"}
              </StatusBadge>
            </div>
            <p className="mt-2 text-2xl font-semibold text-stone-900">{graphTotal.toLocaleString()}</p>
            <p className="text-sm text-stone-600">work object(s)</p>
            {lag != null ? (
              <p className="mt-2 text-xs text-stone-500">
                {lag === 0 ? "Canonical queue caught up (GitHub connection)." : `${lag} raw row(s) queued`}
              </p>
            ) : null}
            <Link
              to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph`}
              className="mt-3 inline-block text-sm font-medium text-blue-700 underline"
            >
              Open execution graph →
            </Link>
          </div>
        </div>
      </OperatorSection>

      <OperatorSection
        title="Operator actions"
        description="Sync pulls fresh data into raw storage. Reset removes a layer so you can rebuild."
      >
        <div className="flex flex-wrap gap-2">
          <Link
            to={`/admin/tenants/${tenantId}/data-pipeline/execution-graph?tab=status`}
            className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium shadow-sm hover:bg-stone-50"
          >
            Pipeline status &amp; advanced reset
          </Link>
        </div>
        <p className="mt-3 text-xs text-stone-500">
          Run sync and per-stage reset controls live in the debug sections below (same APIs as before).
        </p>
      </OperatorSection>

      <CollapsibleDebug title="Debug: Raw ingestion — run sync, reset, inspect records" defaultOpen={focus === "raw"}>
        <AdminTenantStep1 />
      </CollapsibleDebug>

      <CollapsibleDebug title="Debug: Projection rows by entity" defaultOpen={focus === "projections"}>
        <AdminTenantStep2 />
      </CollapsibleDebug>
    </div>
  );
}
