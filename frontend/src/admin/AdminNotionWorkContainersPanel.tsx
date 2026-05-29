import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { AdminNotionWorkContainerRowPreviewModal } from "./AdminNotionWorkContainerRowPreviewModal";
import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type WorkContainerItem = {
  canon_entity_id: string | null;
  database_id: string;
  display_name: string;
  row_count: number;
  is_pinned: boolean;
  is_declared_seed: boolean;
};

type WorkContainersResponse = {
  tenant_id: string;
  max_pins: number;
  items: WorkContainerItem[];
};

export function AdminNotionWorkContainersPanel({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [previewDatabaseId, setPreviewDatabaseId] = useState<string | null>(null);
  const listQ = useQuery({
    queryKey: ["admin-notion-work-containers", tenantId],
    queryFn: () =>
      adminJson<WorkContainersResponse>(`/admin/tenants/${tenantId}/integrations/notion/work-containers`),
    enabled: Boolean(tenantId),
  });

  useEffect(() => {
    if (!listQ.data) return;
    setSelected(new Set(listQ.data.items.filter((item) => item.is_pinned).map((item) => item.database_id)));
  }, [listQ.data]);

  const saveMut = useMutation({
    mutationFn: async (databaseIds: string[]) => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/integrations/notion/work-containers`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ database_ids: databaseIds }),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-notion-work-containers", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-declared-domains-readiness", tenantId] });
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  if (listQ.isLoading) {
    return <p className="text-sm text-stone-600">Loading Notion databases…</p>;
  }
  if (listQ.isError) {
    return <p className="text-sm text-red-700">{(listQ.error as Error).message}</p>;
  }

  const items = listQ.data?.items ?? [];
  const maxPins = listQ.data?.max_pins ?? 30;

  const toggle = (databaseId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(databaseId)) next.delete(databaseId);
      else next.add(databaseId);
      return next;
    });
  };

  return (
    <div className="mt-4 space-y-3 border-t border-stone-200 pt-4">
      <div>
        <h4 className="text-sm font-medium text-stone-900">Declared work containers</h4>
        <p className="mt-1 text-xs text-stone-600">
          Pin Notion databases used as project or roadmap backlogs. Only pinned databases become
          declared domain seeds (max {maxPins}).
        </p>
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {items.length === 0 ? (
        <p className="text-sm text-stone-500">No Notion databases in canon yet. Run ingestion first.</p>
      ) : (
        <ul className="max-h-56 space-y-2 overflow-y-auto">
          {items.map((item) => (
            <li
              key={item.database_id}
              className="flex items-start gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm"
            >
              <input
                type="checkbox"
                className="mt-1"
                checked={selected.has(item.database_id)}
                onChange={() => toggle(item.database_id)}
              />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-stone-900">{item.display_name}</p>
                <p className="font-mono text-xs text-stone-500">{item.database_id}</p>
                <p className="text-xs text-stone-600">
                  {item.row_count.toLocaleString()} rows
                  {item.is_declared_seed ? " · declared seed" : null}
                  {item.row_count > 0 ? (
                    <>
                      {" · "}
                      <button
                        type="button"
                        className="text-indigo-700 underline decoration-indigo-300 hover:text-indigo-900"
                        onClick={() => setPreviewDatabaseId(item.database_id)}
                      >
                        Preview rows
                      </button>
                    </>
                  ) : null}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        className="w-full rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-950 hover:bg-indigo-100 disabled:opacity-50"
        disabled={saveMut.isPending || selected.size > maxPins}
        onClick={() => {
          if (
            !window.confirm(
              "Save pinned work databases? This re-materializes affected rows and enqueues a declared domain pass.",
            )
          ) {
            return;
          }
          saveMut.mutate([...selected]);
        }}
      >
        {saveMut.isPending ? "Saving…" : `Save pins (${selected.size})`}
      </button>
      {previewDatabaseId ? (
        <AdminNotionWorkContainerRowPreviewModal
          tenantId={tenantId}
          databaseId={previewDatabaseId}
          open={Boolean(previewDatabaseId)}
          onClose={() => setPreviewDatabaseId(null)}
        />
      ) : null}
    </div>
  );
}
