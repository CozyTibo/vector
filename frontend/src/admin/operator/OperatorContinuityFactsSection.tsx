import { Link } from "react-router-dom";

import { isCortexAdminV2Enabled } from "./featureFlags";
import type { OperatorContinuityFact } from "./operatorTypes";

const LEGACY_LENS_PATH: Record<string, string> = {
  ingestion: "ingestion",
  runtime: "runtime",
  identity: "identity",
  graph: "graph",
  retrieval: "retrieval",
  queues: "synthesis",
};

const V2_LENS_PATH: Record<string, string> = {
  ingestion: "ingestion",
  runtime: "runtime",
  identity: "inspect/identity",
  graph: "inspect/graph",
  retrieval: "retrieval",
  queues: "synthesis",
};

type Props = {
  facts: OperatorContinuityFact[];
  tenantId: string;
};

export function OperatorContinuityFactsSection({ facts, tenantId }: Props) {
  const lensPath = isCortexAdminV2Enabled() ? V2_LENS_PATH : LEGACY_LENS_PATH;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Continuity facts</h2>
      <ul className="mt-3 space-y-2">
        {facts.map((fact) => {
          const segment = fact.inspect_lens ? lensPath[fact.inspect_lens] ?? "overview" : null;
          return (
            <li key={fact.key} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
              <span className="text-stone-800">{fact.text}</span>
              {segment ? (
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/${segment}`}
                  className="shrink-0 text-xs font-medium text-indigo-700 no-underline hover:underline"
                >
                  Inspect
                </Link>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
