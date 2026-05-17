import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { normalizeRetrievalLegalityClassNames } from "./retrievalAdminSurfaces";

export default function AdminCortexRetrievalLegalityPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["retrieval-legality-detail", tenantId],
    queryFn: () =>
      adminJson<{ retrieval_policy_digest: string; legality_classes: unknown }>(
        `/admin/tenants/${tenantId}/cortex/retrieval/legality`,
      ),
  });

  if (isLoading) return <p className="text-sm text-stone-500">Loading…</p>;
  if (!data) return null;

  const classNames = normalizeRetrievalLegalityClassNames(data.legality_classes);

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 text-sm shadow-sm">
      <h2 className="font-semibold text-stone-900">Retrieval legality classes</h2>
      <p className="mt-2 text-stone-600">
        Retrieval fails closed on replay identity mismatch, traversal degradation without posture,
        chronology illegality, and unresolved continuity.
      </p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-stone-800">
        {classNames.map((c) => (
          <li key={c}>
            <code className="text-xs">{c}</code>
          </li>
        ))}
      </ul>
    </section>
  );
}
