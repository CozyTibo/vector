import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../ui/StatusBadge";
import type { PhaseOverview, PhaseStatus } from "./pipelineTypes";

function statusTone(status: PhaseStatus): "ok" | "warn" | "bad" | "neutral" {
  if (status === "healthy") return "ok";
  if (status === "running") return "neutral";
  if (status === "waiting") return "warn";
  if (status === "blocked") return "bad";
  return "warn";
}

function statusLabel(status: PhaseStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function PipelineStrip({ phases }: { phases: PhaseOverview[] }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex`;

  return (
    <div className="flex flex-wrap gap-2">
      {phases.map((p) => (
        <Link
          key={p.phase}
          to={`${base}/${p.route}`}
          className="min-w-[7.5rem] flex-1 rounded-lg border border-stone-200 bg-stone-50 p-3 no-underline hover:border-indigo-200 hover:bg-indigo-50/40"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">{p.label}</p>
          <div className="mt-1">
            <StatusBadge tone={statusTone(p.status)}>{statusLabel(p.status)}</StatusBadge>
          </div>
          {p.detail ? <p className="mt-1 line-clamp-2 text-[11px] text-stone-600">{p.detail}</p> : null}
        </Link>
      ))}
    </div>
  );
}
