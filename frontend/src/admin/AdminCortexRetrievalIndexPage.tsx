import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

export default function AdminCortexRetrievalIndexPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const indexQ = useQuery({
    queryKey: ["retrieval-index", tenantId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(`/admin/tenants/${tenantId}/cortex/retrieval/index`),
  });

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Index materialization</h2>
        <p className="mt-2 text-sm text-stone-600">
          Rebuild indexes from{" "}
          <Link className="font-medium text-indigo-700 underline" to={`/admin/tenants/${tenantId}/cortex/overview`}>
            Overview
          </Link>{" "}
          → Start from step → Retrieval (execution engine only).
        </p>
        {indexQ.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {indexQ.data && (
          <pre className="mt-3 max-h-[20rem] overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-xs">
            {JSON.stringify(indexQ.data, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}
