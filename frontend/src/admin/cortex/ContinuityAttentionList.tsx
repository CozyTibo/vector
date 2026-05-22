import { Link, useParams } from "react-router-dom";

import type { AttentionItem } from "./pipelineTypes";

const priorityStyles: Record<AttentionItem["priority"], string> = {
  P0: "border-red-300 bg-red-50 text-red-950",
  P1: "border-amber-300 bg-amber-50 text-amber-950",
  P2: "border-stone-300 bg-stone-50 text-stone-900",
};

export function ContinuityAttentionList({ items }: { items: AttentionItem[] }) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex`;

  if (items.length === 0) return null;

  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-amber-950">What needs attention</h3>
      <p className="mt-1 text-xs text-amber-900/80">
        Root causes first — downstream symptoms suppressed when upstream explains the failure.
      </p>
      <ol className="mt-4 space-y-3">
        {items.map((item) => (
          <li
            key={`${item.priority}-${item.title}`}
            className={`rounded-lg border px-4 py-3 text-sm ${priorityStyles[item.priority]}`}
          >
            <p className="font-semibold">
              [{item.priority}] {item.title}
            </p>
            <p className="mt-1">
              <span className="font-medium">Impact:</span> {item.impact}
            </p>
            <p className="mt-1">
              <span className="font-medium">Action:</span> {item.action}
            </p>
            {item.phase ? (
              <p className="mt-2 text-xs">
                <Link to={`${base}/${item.phase === "reconstruction" ? "reconstruction" : item.phase}`} className="font-medium text-indigo-800 underline">
                  Open {item.phase} tab
                </Link>
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
