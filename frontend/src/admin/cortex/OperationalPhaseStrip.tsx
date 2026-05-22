import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../ui/StatusBadge";
import type { PhaseStatus, PipelineOverviewPhase } from "./pipelineTypes";
import { OPERATOR_PHASES } from "./pipelineTypes";

function statusTone(status: PhaseStatus): "ok" | "warn" | "bad" | "neutral" {
  if (status === "healthy") return "ok";
  if (status === "running") return "neutral";
  if (status === "waiting") return "warn";
  if (status === "blocked") return "bad";
  return "warn";
}

export function phasesForOperationalStrip(
  phases: PipelineOverviewPhase[] | undefined,
): OperationalPhase[] {
  return OPERATOR_PHASES.map((meta) => {
    const row = phases?.find((p) => p.phase === meta.phase);
    const status = row?.status ?? "waiting";
    const statusLabel =
      row?.status_label?.trim() ||
      (status === "healthy"
        ? "Healthy"
        : status === "running"
          ? "Running"
          : status === "blocked"
            ? "Blocked"
            : status === "degraded"
              ? "Degraded"
              : "Waiting");
    return {
      ...meta,
      status,
      statusLabel,
      headline: row?.headline ?? "",
      signals: row?.signals ?? [],
      continuityAdvancing: row?.continuity_advancing ?? false,
      objectCountLabel: null,
    };
  });
}

export type OperationalPhase = {
  phase: PipelineOverviewPhase["phase"];
  label: string;
  route: string;
  status: PhaseStatus;
  statusLabel: string;
  headline: string;
  signals: NonNullable<PipelineOverviewPhase["signals"]>;
  continuityAdvancing: boolean;
  objectCountLabel: null;
};

export function OperationalPhaseStrip({ phases }: { phases: OperationalPhase[] }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex`;

  return (
    <div className="flex flex-wrap gap-2">
      {phases.map((p) => (
        <Link
          key={p.phase}
          to={`${base}/${p.route}`}
          className="min-w-[8.5rem] flex-1 rounded-lg border border-stone-200 bg-stone-50 p-3 no-underline hover:border-indigo-200 hover:bg-indigo-50/40"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">{p.label}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1">
            <StatusBadge tone={statusTone(p.status)}>{p.statusLabel}</StatusBadge>
            {p.continuityAdvancing ? (
              <span className="text-[10px] text-emerald-700">advancing</span>
            ) : (
              <span className="text-[10px] text-amber-800">stalled</span>
            )}
          </div>
          <p className="mt-2 line-clamp-2 text-xs font-medium text-stone-800">
            {p.headline || "—"}
          </p>
          <ul className="mt-2 space-y-0.5">
            {(p.signals ?? []).slice(0, 3).map((s) => (
              <li key={s.key} className="flex justify-between gap-2 text-[10px] text-stone-600">
                <span className="truncate">{s.label}</span>
                <span
                  className={
                    s.severity === "bad"
                      ? "font-semibold text-red-800"
                      : s.severity === "warn"
                        ? "font-medium text-amber-900"
                        : "tabular-nums text-stone-800"
                  }
                >
                  {s.value}
                </span>
              </li>
            ))}
          </ul>
        </Link>
      ))}
    </div>
  );
}
