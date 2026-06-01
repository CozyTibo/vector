import { Link, useParams } from "react-router-dom";

import type { ConnectedWorkChain } from "./executionSurfacesTypes";
import { OmissionBanner } from "./OmissionBanner";

export function ConnectedWorkChains({
  chains,
  omission,
}: {
  chains: ConnectedWorkChain[];
  omission: { code: string; message: string; remediation: string | null } | null;
}) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  if (!chains.length) {
    return (
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-stone-900">Connected work</h3>
        <OmissionBanner omission={omission} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-stone-900">Connected work</h3>
      <p className="text-sm text-stone-600">
        Cross-tool execution chains reconstructed from graph relationships. Each hop shows relationship kind and
        evidence.
      </p>
      {chains.map((chain, idx) => (
        <div key={idx} className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
          <ol className="space-y-3">
            {chain.hops.map((hop, hopIdx) => (
              <li key={hopIdx} className="flex flex-col gap-1">
                {hopIdx > 0 && hop.relationship ? (
                  <div className="flex items-center gap-2 text-xs text-indigo-800">
                    <span className="font-medium">↓ {hop.relationship.relationship_kind_label}</span>
                    <span className="text-stone-500">· {hop.relationship.confidence}</span>
                  </div>
                ) : null}
                <div className="rounded-lg border border-white bg-white px-3 py-2 shadow-sm">
                  <Link
                    to={`/admin/tenants/${tenantId}/cortex/execution-surfaces/work/${hop.entity.entity_id}`}
                    className="font-medium text-indigo-800 hover:underline"
                  >
                    {hop.entity.display_label}
                  </Link>
                  <p className="text-xs text-stone-500">
                    {hop.entity.entity_type} · {hop.entity.connector}
                  </p>
                  {hop.relationship ? (
                    <p className="mt-1 font-mono text-xs text-stone-600">
                      {hop.relationship.extractor_rule} · {hop.relationship.evidence_ref}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
