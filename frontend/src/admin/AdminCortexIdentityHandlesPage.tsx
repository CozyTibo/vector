import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import type { CortexIdentityHandlesExplorerResponse } from "./cortexAdminTypes";

export default function AdminCortexIdentityHandlesPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-identity-handles", tenantId],
    queryFn: () =>
      adminJson<CortexIdentityHandlesExplorerResponse>(
        `/admin/tenants/${tenantId}/cortex/identity/handles?limit=200`,
      ),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (q.isPending) return <p className="text-sm text-stone-600">Loading org handles…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;

  const rows = q.data.rows;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Phase 04</p>
          <h1 className="mt-1 text-xl font-semibold text-stone-900">Org handles</h1>
          <p className="mt-1 text-sm text-stone-600">
            Explorer rows (<span className="font-mono">org_handle_list_row_v1</span>). One row per org entity
            (handle).
          </p>
        </div>
        <Link
          to={`/admin/tenants/${tenantId}/cortex/entity-resolution`}
          className="text-sm font-medium text-indigo-700 hover:text-indigo-900"
        >
          ← Identity overview
        </Link>
      </div>

      <p className="text-xs text-stone-500">
        Showing {rows.length} of up to 200 · schema v{q.data.identity_operator_console_schema_version}
      </p>

      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-stone-200 text-sm">
          <thead className="bg-stone-50 text-left text-xs font-medium uppercase tracking-wide text-stone-600">
            <tr>
              <th className="px-3 py-2">Handle id</th>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Created from</th>
              <th className="px-3 py-2 text-right">Personas</th>
              <th className="px-3 py-2 text-right">Active links</th>
              <th className="px-3 py-2">Temporal</th>
              <th className="px-3 py-2">Merge</th>
              <th className="px-3 py-2">Replay</th>
              <th className="px-3 py-2">Confidence</th>
              <th className="px-3 py-2 text-right">Cand. persona</th>
              <th className="px-3 py-2 text-right">Cand. any</th>
              <th className="px-3 py-2 text-right">Ambiguity</th>
              <th className="px-3 py-2">Kind rule</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {rows.map((r) => (
              <tr key={r.handle_id} className="hover:bg-stone-50">
                <td className="px-3 py-2 font-mono text-xs">
                  <Link
                    to={`/admin/tenants/${tenantId}/cortex/identity/handles/${r.handle_id}`}
                    className="text-indigo-700 hover:text-indigo-900"
                  >
                    {r.handle_id}
                  </Link>
                </td>
                <td className="px-3 py-2 text-stone-800">{r.kind}</td>
                <td className="px-3 py-2 text-xs text-stone-600">{r.created_from}</td>
                <td className="px-3 py-2 text-right tabular-nums">{r.persona_count}</td>
                <td className="px-3 py-2 text-right tabular-nums">{r.active_links}</td>
                <td className="px-3 py-2 text-xs">{r.temporal_state}</td>
                <td className="px-3 py-2 text-xs">{r.merge_state}</td>
                <td className="px-3 py-2 text-xs">{r.last_replay}</td>
                <td className="px-3 py-2 text-xs">{r.confidence_posture}</td>
                <td className="px-3 py-2 text-right tabular-nums text-xs">
                  {r.candidate_persona_touch_count ?? 0}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-xs">
                  {r.candidate_any_touch_count ?? 0}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-xs">
                  {r.open_ambiguity_touch_count ?? 0}
                </td>
                <td className="max-w-[10rem] truncate px-3 py-2 font-mono text-[10px] text-stone-600">
                  {r.entity_kind_rule ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
