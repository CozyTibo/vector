import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

export default function AdminCortexReasoningCertificationPackPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const q = useQuery({
    queryKey: ["reasoning-cert-pack", tenantId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/reasoning/certification-pack`,
      ),
  });

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Static certification pack</h2>
      <p className="mt-1 text-sm text-stone-600">
        Program-level closure snapshot (G-P06-CLOSE-01). Distinct from per-tenant runtime reconstruction
        jobs.
      </p>
      {q.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      {q.error && <p className="mt-2 text-sm text-red-600">{(q.error as Error).message}</p>}
      {q.data && (
        <dl className="mt-4 grid gap-2 text-sm">
          <div>
            <dt className="text-stone-500">Closure passed</dt>
            <dd>{String(q.data.closure_passed)}</dd>
          </div>
          {typeof q.data.whole_file_sha256 === "string" && (
            <div>
              <dt className="text-stone-500">Pack digest</dt>
              <dd className="font-mono text-xs break-all">{q.data.whole_file_sha256}</dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}
