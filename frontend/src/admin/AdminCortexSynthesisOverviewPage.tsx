import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type HealthStrip = {
  substrate_state?: string;
  replay_posture?: string;
  publication_epoch?: string | null;
  synthesis_completeness_percent?: number;
};

type Overview = {
  health_strip?: HealthStrip;
  coverage_percent?: number;
  eligible_scopes?: number;
  synthesized_scopes?: number;
};

export default function AdminCortexSynthesisOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/synthesis`;

  const { data, isLoading } = useQuery({
    queryKey: ["synthesis-overview", tenantId],
    queryFn: () => adminJson<Overview>(`/admin/tenants/${tenantId}/cortex/synthesis/overview`),
  });

  const health = data?.health_strip;

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-stone-900">Synthesis overview</h2>
      <p className="mt-1 text-sm text-stone-600">
        Substrate completeness, health strip, and links to operator debuggers.
      </p>
      {isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
      {data && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={health?.substrate_state === "healthy" ? "ok" : "warn"}>
              {health?.substrate_state ?? "unknown"}
            </StatusBadge>
            <span className="text-stone-600">replay: {health?.replay_posture ?? "—"}</span>
            <span className="text-stone-600">
              coverage: {data.coverage_percent ?? health?.synthesis_completeness_percent ?? 0}%
            </span>
          </div>
          <p className="text-stone-600">
            Eligible {data.eligible_scopes ?? 0} · synthesized {data.synthesized_scopes ?? 0}
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link className="text-violet-700 underline" to={`${base}/workflows`}>
              Operator workflows (W1–W4)
            </Link>
            <Link className="text-violet-700 underline" to={`${base}/control-plane`}>
              Control plane
            </Link>
            <Link className="text-violet-700 underline" to={`${base}/jobs`}>
              Job debugger
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
