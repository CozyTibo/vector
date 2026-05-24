import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { readErrorDetail } from "../../lib/canonicalApi";
import { CORTEX_MANUAL_SYNC_CONFIRM_PHRASE } from "../adminConstants";
import { titleConnector } from "../cortexAdminTypes";
import { SectionSkeleton } from "../cortex/SectionSkeleton";
import { invalidateOperatorOverviewCaches } from "./useOperatorOverview";
import type { OperatorConnectorRow } from "./operatorTypes";

function syncAge(row: OperatorConnectorRow): string {
  const latest = row.latest_run;
  const ts = (latest?.finished_at ?? latest?.started_at ?? row.checkpoint_last_incremental_at) as
    | string
    | undefined;
  if (!ts) return "never";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  const hours = (Date.now() - d.getTime()) / 3_600_000;
  if (hours < 1) return "<1h ago";
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function statusLabel(row: OperatorConnectorRow): string {
  const latest = row.latest_run as { status?: string } | null;
  if (!row.connection_id) return "not connected";
  if (row.connection_status !== "active") return row.connection_status ?? "inactive";
  if (!row.cortex_routed) return "not routed";
  return (latest?.status ?? "idle").toLowerCase();
}

type Props = {
  connectors: OperatorConnectorRow[];
  loading?: boolean;
};

export function OperatorConnectorsTable({ connectors, loading }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const syncMut = useMutation({
    mutationFn: async (connector: string) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/ingestion/actions/trigger-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          connector,
          confirmation: CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => invalidateOperatorOverviewCaches(qc, tenantId),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Connectors</h2>
      {loading ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-xs uppercase tracking-wide text-stone-500">
                <th className="py-2 pr-4">Connector</th>
                <th className="py-2 pr-4">Last sync</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {connectors.map((row) => (
                <tr key={row.connector} className="border-b border-stone-100">
                  <td className="py-2 pr-4 font-medium text-stone-900">{titleConnector(row.connector)}</td>
                  <td className="py-2 pr-4 text-stone-600">{syncAge(row)}</td>
                  <td className="py-2 pr-4 text-stone-600">{statusLabel(row)}</td>
                  <td className="py-2">
                    <button
                      type="button"
                      className="text-xs font-medium text-indigo-700 hover:underline disabled:opacity-40"
                      disabled={
                        syncMut.isPending ||
                        !row.cortex_routed ||
                        row.connection_status !== "active"
                      }
                      onClick={() => syncMut.mutate(row.connector)}
                    >
                      Sync now
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {syncMut.isError ? (
        <p className="mt-2 text-xs text-red-700">{(syncMut.error as Error).message}</p>
      ) : null}
    </section>
  );
}
