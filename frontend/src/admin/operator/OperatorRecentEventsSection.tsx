import { Link } from "react-router-dom";

import type { OperatorRecentEvent } from "./operatorTypes";

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type Props = {
  events: OperatorRecentEvent[];
  tenantId: string;
};

export function OperatorRecentEventsSection({ events, tenantId }: Props) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Recent events</h2>
      <p className="mt-1 text-xs text-stone-500">Ingestion runs and execution transitions (newest first)</p>
      {events.length === 0 ? (
        <p className="mt-3 text-sm text-stone-600">No recent events recorded.</p>
      ) : (
        <ul className="mt-3 divide-y divide-stone-100">
          {events.map((event, idx) => (
            <li key={`${event.kind}-${event.at}-${idx}`} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div>
                <p className="text-sm text-stone-800">{event.summary}</p>
                <p className="text-xs text-stone-500">{fmtTime(event.at)}</p>
              </div>
              <Link
                to={
                  event.kind === "ingestion_run"
                    ? `/admin/tenants/${tenantId}/cortex/ingestion?tab=runs`
                    : `/admin/tenants/${tenantId}/cortex/graph`
                }
                className="text-xs font-medium text-indigo-700 no-underline hover:underline"
              >
                Open
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
