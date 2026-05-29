import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type {
  GraphRelationshipList,
  GraphRelationshipListItem,
  GraphUnresolvedItem,
  GraphUnresolvedList,
} from "../cortexAdminTypes";
import { SectionSkeleton } from "./SectionSkeleton";

const PAGE_SIZE = 50;

const KIND_BROWSE_PRESETS: { kind: string; label: string }[] = [
  { kind: "authored_by", label: "Authored by" },
  { kind: "assigned_to", label: "Assigned to" },
  { kind: "attached_to", label: "Attached to" },
  { kind: "replies_to", label: "Replies to" },
  { kind: "comments_on", label: "Comments on" },
  { kind: "belongs_to_repo", label: "Belongs to repo" },
  { kind: "parent_of", label: "Parent of" },
  { kind: "relates_to", label: "Relates to" },
  { kind: "references", label: "References" },
  { kind: "mentions", label: "Mentions" },
  { kind: "merged_as_commit", label: "Merged as commit" },
  { kind: "deploys", label: "Deploys" },
];

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function GraphDataTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") === "unresolved" ? "unresolved" : "links";
  const kindFilter = searchParams.get("kind")?.trim() ?? "";
  const entityFilter = searchParams.get("entity_id")?.trim() ?? "";
  const page = Math.max(0, Number.parseInt(searchParams.get("page") ?? "0", 10) || 0);
  const offset = page * PAGE_SIZE;

  const linksQ = useQuery({
    queryKey: ["admin-cortex-graph-relationships", tenantId, kindFilter, entityFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      if (kindFilter) params.set("kind", kindFilter);
      if (entityFilter) params.set("entity_id", entityFilter);
      return adminJson<GraphRelationshipList>(
        `/admin/tenants/${tenantId}/cortex/graph/relationships?${params}`,
      );
    },
    enabled: Boolean(tenantId) && view === "links",
  });

  const unresolvedQ = useQuery({
    queryKey: ["admin-cortex-graph-unresolved", tenantId, page],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      return adminJson<GraphUnresolvedList>(
        `/admin/tenants/${tenantId}/cortex/graph/unresolved?${params}`,
      );
    },
    enabled: Boolean(tenantId) && view === "unresolved",
  });

  const patchParams = (patch: Record<string, string | null>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", "data");
      for (const [key, value] of Object.entries(patch)) {
        if (value == null || value === "") next.delete(key);
        else next.set(key, value);
      }
      return next;
    });
  };

  const activeKindPreset = KIND_BROWSE_PRESETS.find((row) => row.kind === kindFilter);

  const setView = (next: "links" | "unresolved") => {
    patchParams({ view: next === "links" ? null : next, page: null });
  };

  const activeQ = view === "links" ? linksQ : unresolvedQ;
  const total =
    view === "links" ? (linksQ.data?.total_count ?? 0) : (unresolvedQ.data?.total_count ?? 0);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-stone-900">Data</h2>
          <p className="text-sm text-stone-600">Active links and unresolved reference tokens</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className={[
              "rounded-md px-3 py-1.5 text-sm font-medium",
              view === "links"
                ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                : "text-stone-700 hover:bg-stone-100",
            ].join(" ")}
            onClick={() => setView("links")}
          >
            Links
          </button>
          <button
            type="button"
            className={[
              "rounded-md px-3 py-1.5 text-sm font-medium",
              view === "unresolved"
                ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                : "text-stone-700 hover:bg-stone-100",
            ].join(" ")}
            onClick={() => setView("unresolved")}
          >
            Unresolved
          </button>
        </div>
      </div>

      {view === "links" ? (
        <div className="mt-4 space-y-3">
          {kindFilter ? (
            <div className="rounded-lg border border-indigo-100 bg-indigo-50/60 px-4 py-3">
              <p className="text-sm font-medium text-indigo-950">
                Browsing{" "}
                {activeKindPreset?.label ??
                  kindFilter.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                <span className="ml-2 font-mono text-xs font-normal text-indigo-800/80">
                  ({kindFilter})
                </span>
              </p>
              <p className="mt-1 text-xs text-indigo-900/80">
                Review source → target pairs and extractor rules for this relationship kind.
              </p>
              <button
                type="button"
                className="mt-2 text-xs font-medium text-indigo-800 hover:underline"
                onClick={() => patchParams({ kind: null, page: null })}
              >
                Clear kind filter
              </button>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <span className="self-center text-xs text-stone-500">Browse by kind:</span>
            {KIND_BROWSE_PRESETS.map((preset) => (
              <button
                key={preset.kind}
                type="button"
                className={[
                  "rounded-md px-2.5 py-1 text-xs font-medium",
                  kindFilter === preset.kind
                    ? "bg-indigo-100 text-indigo-900 ring-1 ring-inset ring-indigo-200"
                    : "border border-stone-200 bg-white text-stone-700 hover:bg-stone-50",
                ].join(" ")}
                onClick={() =>
                  patchParams({
                    kind: kindFilter === preset.kind ? null : preset.kind,
                    page: null,
                  })
                }
              >
                {preset.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-3">
          <label className="text-xs text-stone-600">
            Relationship kind
            <input
              className="mt-1 block w-48 rounded border border-stone-200 px-2 py-1 text-sm font-mono"
              placeholder="e.g. authored_by"
              value={kindFilter}
              onChange={(e) => patchParams({ kind: e.target.value || null, page: null })}
            />
          </label>
          <label className="text-xs text-stone-600">
            Canon entity id
            <input
              className="mt-1 block min-w-[16rem] rounded border border-stone-200 px-2 py-1 text-sm font-mono"
              placeholder="UUID"
              value={entityFilter}
              onChange={(e) => patchParams({ entity_id: e.target.value || null, page: null })}
            />
          </label>
          </div>
        </div>
      ) : null}

      <p className="mt-3 text-xs text-stone-500">
        {total === 0
          ? view === "links"
            ? "No active execution links match these filters."
            : "No unresolved reference tokens."
          : `${total.toLocaleString()} row(s)`}
      </p>

      {activeQ.isPending ? (
        <div className="mt-4">
          <SectionSkeleton variant="table" />
        </div>
      ) : activeQ.isError ? (
        <p className="mt-4 text-sm text-red-700">{(activeQ.error as Error).message}</p>
      ) : view === "links" ? (
        <LinksList items={linksQ.data?.items ?? []} tenantId={tenantId} />
      ) : (
        <UnresolvedList items={unresolvedQ.data?.items ?? []} tenantId={tenantId} />
      )}

      {total > PAGE_SIZE ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
            disabled={page <= 0}
            onClick={() => patchParams({ page: page <= 1 ? null : String(page - 1) })}
          >
            Previous
          </button>
          <span className="text-xs text-stone-600">
            Page {page + 1} of {pageCount}
          </span>
          <button
            type="button"
            className="rounded border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-800 disabled:opacity-40"
            disabled={page + 1 >= pageCount}
            onClick={() => patchParams({ page: String(page + 1) })}
          >
            Next
          </button>
        </div>
      ) : null}
    </section>
  );
}

function LinksList({
  items,
  tenantId,
}: {
  items: GraphRelationshipListItem[];
  tenantId: string;
}) {
  if (items.length === 0) {
    return <p className="mt-4 text-sm text-stone-500">No active execution links yet.</p>;
  }
  return (
    <ul className="mt-4 divide-y divide-stone-100 rounded-lg border border-stone-200">
      {items.map((row) => (
        <li key={row.id} className="space-y-1 p-4 text-sm">
          <p className="font-medium text-stone-900">
            <span className="text-indigo-800">{row.relationship_kind_label}</span>
            <span className="font-mono text-xs text-stone-500"> ({row.relationship_kind})</span>
            <span className="text-stone-400"> · {row.confidence}</span>
          </p>
          <p className="text-stone-700">
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.from.entity_id}`}
            >
              {row.from.display_label ?? row.from.entity_id}
            </Link>
            <span className="mx-2 text-stone-400">→</span>
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.to.entity_id}`}
            >
              {row.to.display_label ?? row.to.entity_id}
            </Link>
          </p>
          <p className="font-mono text-xs text-stone-500">
            {row.extractor_rule} · {formatWhen(row.observed_at)}
          </p>
        </li>
      ))}
    </ul>
  );
}

function UnresolvedList({
  items,
  tenantId,
}: {
  items: GraphUnresolvedItem[];
  tenantId: string;
}) {
  if (items.length === 0) {
    return <p className="mt-4 text-sm text-stone-500">No unresolved reference tokens.</p>;
  }
  return (
    <ul className="mt-4 divide-y divide-stone-100 rounded-lg border border-stone-200 text-sm">
      {items.map((row) => (
        <li key={row.id} className="space-y-1 p-4">
          <p className="font-mono text-stone-800">{row.reference_text}</p>
          <p className="text-stone-600">
            {row.reference_kind} · {row.extractor_rule}
          </p>
          {row.source_entity ? (
            <Link
              className="text-indigo-700 hover:underline"
              to={`/admin/tenants/${tenantId}/cortex/canon/entities/${row.source_entity.entity_id}`}
            >
              {row.source_entity.display_label}
            </Link>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
