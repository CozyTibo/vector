import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";

import { executionSurfacesAdminPath } from "../../lib/adminApiUrl";
import { adminJson } from "../../lib/adminFetch";
import { CortexPageSkeleton } from "../cortex/CortexPageSkeleton";
import { ObservationFootnote, OmissionBanner } from "./OmissionBanner";

type ActivityResponse = {
  items: Array<Record<string, unknown>>;
  total_count: number;
  execution_timeline_available: boolean;
  footnote: string;
  window_hours: number;
};

export function ActivityTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const hours = Number(searchParams.get("hours") ?? "168");
  const entityType = searchParams.get("entity_type") ?? "";

  const q = useQuery({
    queryKey: ["execution-surface-activity", tenantId, hours, entityType],
    enabled: Boolean(tenantId),
    queryFn: () => {
      const params = new URLSearchParams({ hours: String(hours), limit: "80" });
      if (entityType) params.set("entity_type", entityType);
      return adminJson<ActivityResponse>(
        executionSurfacesAdminPath(tenantId, "activity", params),
        undefined,
        { tenantIdHint: tenantId },
      );
    },
  });

  if (q.isLoading) return <CortexPageSkeleton label="Loading activity" />;

  const data = q.data;

  return (
    <div className="space-y-4">
      <ObservationFootnote text={data?.footnote ?? ""} />
      {!data?.execution_timeline_available ? (
        <OmissionBanner
          omission={{
            code: "execution_timeline_not_available",
            message: "This stream shows Cortex observation signals only (graph + membership).",
            remediation: "Operational execution events require future canon timeline support.",
          }}
        />
      ) : null}
      <div className="flex flex-wrap gap-2">
        {([24, 168, 720] as const).map((h) => (
          <button
            key={h}
            type="button"
            className={`rounded px-2 py-1 text-sm ${
              hours === h ? "bg-indigo-100 text-indigo-900" : "bg-stone-100"
            }`}
            onClick={() =>
              setSearchParams((prev) => {
                const p = new URLSearchParams(prev);
                p.set("tab", "activity");
                p.set("hours", String(h));
                return p;
              })
            }
          >
            {h === 24 ? "24h" : h === 168 ? "7d" : "30d"}
          </button>
        ))}
        <select
          className="rounded border border-stone-200 px-2 py-1 text-sm"
          value={entityType}
          onChange={(e) =>
            setSearchParams((prev) => {
              const p = new URLSearchParams(prev);
              p.set("tab", "activity");
              if (e.target.value) p.set("entity_type", e.target.value);
              else p.delete("entity_type");
              return p;
            })
          }
        >
          <option value="">All types</option>
          <option value="work_item">Work items</option>
          <option value="pull_request">PRs</option>
          <option value="document">Documents</option>
          <option value="message">Messages</option>
        </select>
      </div>
      <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
        {(data?.items ?? []).map((ev) => (
          <li key={String(ev.id)} className="px-4 py-3 text-sm">
            <p className="font-medium text-stone-900">{String(ev.label)}</p>
            <p className="text-xs text-stone-500">{String(ev.observed_at)}</p>
            <p className="font-mono text-xs text-stone-600">
              {String((ev.provenance as Record<string, unknown>)?.extractor_rule ?? "")}
            </p>
          </li>
        ))}
      </ul>
      {data && data.items.length === 0 ? (
        <OmissionBanner
          omission={{
            code: "no_observation_signals",
            message: "No observation signals in this time window.",
            remediation: "Improve graph and declared domain passes.",
          }}
        />
      ) : null}
    </div>
  );
}
