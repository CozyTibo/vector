import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

export default function AdminCortexReasoningLegalityPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const q = useQuery({
    queryKey: ["reasoning-runtime-legality", tenantId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/reasoning/runtime-legality-matrix`,
      ),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Runtime legality matrix</h2>
      {q.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      {q.error && <p className="mt-2 text-sm text-red-600">{(q.error as Error).message}</p>}
      {q.data && (
        <pre className="mt-4 max-h-[32rem] overflow-auto rounded bg-stone-50 p-3 text-xs">
          {JSON.stringify(q.data, null, 2)}
        </pre>
      )}
    </section>
  );
}
