import { useQuery } from "@tanstack/react-query";

import { adminJson } from "../lib/adminFetch";

type RowSample = {
  row_id: string;
  title: string;
};

type RowSamplesResponse = {
  tenant_id: string;
  database_id: string;
  display_name: string;
  row_count: number;
  samples: RowSample[];
};

type Props = {
  tenantId: string;
  databaseId: string;
  open: boolean;
  onClose: () => void;
};

export function AdminNotionWorkContainerRowPreviewModal({
  tenantId,
  databaseId,
  open,
  onClose,
}: Props) {
  const samplesQ = useQuery({
    queryKey: ["admin-notion-work-container-row-samples", tenantId, databaseId],
    queryFn: () =>
      adminJson<RowSamplesResponse>(
        `/admin/tenants/${tenantId}/integrations/notion/work-containers/${encodeURIComponent(databaseId)}/row-samples`,
      ),
    enabled: open && Boolean(tenantId) && Boolean(databaseId),
    staleTime: 60_000,
  });

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="notion-row-preview-title"
      onClick={onClose}
    >
      <div
        className="max-h-[80vh] w-full max-w-lg overflow-hidden rounded-xl border border-stone-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-stone-200 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 id="notion-row-preview-title" className="text-lg font-semibold text-stone-900">
                {samplesQ.data?.display_name ?? "Sample rows"}
              </h2>
              <p className="mt-0.5 font-mono text-xs text-stone-500">{databaseId}</p>
              {samplesQ.data ? (
                <p className="mt-1 text-xs text-stone-600">
                  {samplesQ.data.row_count.toLocaleString()} rows total · showing recent samples
                </p>
              ) : null}
            </div>
            <button
              type="button"
              className="rounded-lg px-2 py-1 text-sm text-stone-600 hover:bg-stone-100"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
        <div className="max-h-[50vh] overflow-y-auto px-4 py-3">
          {samplesQ.isLoading ? (
            <p className="text-sm text-stone-600">Loading sample rows…</p>
          ) : samplesQ.isError ? (
            <p className="text-sm text-red-700">{(samplesQ.error as Error).message}</p>
          ) : samplesQ.data?.samples.length ? (
            <ol className="list-decimal space-y-2 pl-5 text-sm text-stone-800">
              {samplesQ.data.samples.map((sample) => (
                <li key={sample.row_id} className="leading-snug">
                  {sample.title}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-stone-500">No row titles found for this database.</p>
          )}
        </div>
      </div>
    </div>
  );
}
