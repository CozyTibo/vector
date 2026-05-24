import { Link, useParams, useSearchParams } from "react-router-dom";

import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { DeployInfoFooter } from "../DeployInfoFooter";
import { useOperatorRetrievalLineage } from "../useOperatorInspectChains";
import { LineageChainPanel } from "./LineageChainPanel";

export default function OperatorRetrievalLineageInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams] = useSearchParams();
  const kind = searchParams.get("kind") ?? "";
  const ref = searchParams.get("ref") ?? "";
  const lineageQ = useOperatorRetrievalLineage(kind, ref, Boolean(kind && ref));

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <Link
          to={`/admin/tenants/${tenantId}/cortex/inspect/retrieval`}
          className="text-xs font-medium text-indigo-700 no-underline hover:underline"
        >
          ← Retrieval inspect
        </Link>
        <h1 className="mt-2 text-lg font-semibold text-stone-900">Retrieval lineage</h1>
        <p className="mt-1 font-mono text-sm text-stone-600">
          {kind || "—"} / {ref || "—"}
        </p>
      </header>

      {!kind || !ref ? (
        <p className="text-sm text-stone-600">Provide kind and ref query params to load lineage.</p>
      ) : lineageQ.isPending ? (
        <SectionSkeleton variant="attention" />
      ) : lineageQ.isError ? (
        <p className="text-sm text-red-700">{(lineageQ.error as Error).message}</p>
      ) : lineageQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <LineageChainPanel chain={lineageQ.data.chain} />
        </section>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}
