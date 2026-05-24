import { Link } from "react-router-dom";

import type { OperatorStatusBanner } from "./operatorTypes";

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

type Props = {
  banner: OperatorStatusBanner;
  tenantId: string;
};

export function OperatorStatusBannerSection({ banner, tenantId }: Props) {
  const headline = [
    banner.lease_status?.toUpperCase() ?? "UNKNOWN",
    banner.phase_cursor ? `· ${banner.phase_cursor.replace(/_/g, " ")}` : null,
    banner.block_reason_code ? `· blocked: ${banner.block_reason_code}` : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className="rounded-xl border border-stone-300 bg-stone-900 px-5 py-4 text-stone-100 shadow-sm">
      <p className="text-sm font-semibold tracking-wide">{headline || "Execution status unknown"}</p>
      <p className="mt-2 text-xs text-stone-300">
        FSM {banner.fsm_state ?? "—"}
        {banner.obligation_epoch != null ? ` · obligation ${banner.obligation_epoch}` : ""}
        {banner.target_epoch != null ? ` → target ${banner.target_epoch}` : ""}
      </p>
      {banner.last_transition_at ? (
        <p className="mt-1 text-xs text-stone-400">
          Last transition: {fmtTime(banner.last_transition_at)}
          {banner.last_transition_from_state && banner.last_transition_to_state
            ? ` · ${banner.last_transition_from_state} → ${banner.last_transition_to_state}`
            : ""}
        </p>
      ) : null}
      <div className="mt-3">
        <Link
          to={`/admin/tenants/${tenantId}/cortex/inspect`}
          className="text-xs font-medium text-indigo-300 no-underline hover:underline"
        >
          Open execution detail →
        </Link>
      </div>
    </section>
  );
}
