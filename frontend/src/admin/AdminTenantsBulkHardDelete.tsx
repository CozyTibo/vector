import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { HARD_DELETE_TENANT_CONFIRMATION_PHRASE } from "./adminConstants";
import type { PendingTenantDelete } from "./pendingTenantDeletes";

export type BulkTenant = {
  id: string;
  company_name: string;
};

type BulkAcceptedResponse = {
  accepted: boolean;
  task_id: string;
  queue: string;
  tenant_count: number;
  tenant_ids: string[];
  company_names: string[];
};

type Props = {
  tenants: BulkTenant[];
  onCancel: () => void;
  /** Called immediately after the delete job is enqueued (not when DB work finishes). */
  onAccepted: (result: { pending: PendingTenantDelete[] }) => void;
};

/**
 * Destructive confirmation: phrase + one company name per line (sorted by name),
 * matching the numbered list shown in the dialog.
 */
export default function AdminTenantsBulkHardDelete({ tenants, onCancel, onAccepted }: Props) {
  const sorted = useMemo(
    () => [...tenants].sort((a, b) => a.company_name.localeCompare(b.company_name)),
    [tenants],
  );
  const expectedLines = useMemo(
    () => sorted.map((t) => t.company_name.trim()),
    [sorted],
  );

  const [phraseConfirm, setPhraseConfirm] = useState("");
  const [linesConfirm, setLinesConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setPhraseConfirm("");
    setLinesConfirm("");
    setErr(null);
  }, [tenants]);

  const linesMatch = useMemo(() => {
    const lines = linesConfirm
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (lines.length !== expectedLines.length) {
      return false;
    }
    return lines.every((l, i) => l === expectedLines[i]);
  }, [linesConfirm, expectedLines]);

  const canSubmit =
    phraseConfirm === HARD_DELETE_TENANT_CONFIRMATION_PHRASE && linesMatch && sorted.length > 0;

  const deleteMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch("/admin/tenants/hard-delete-bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confirmation: phraseConfirm.trim(),
          tenants: sorted.map((t) => ({
            tenant_id: t.id,
            company_name_confirmation: t.company_name.trim(),
          })),
        }),
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return (await res.json()) as BulkAcceptedResponse;
    },
    onSuccess: (data) => {
      const pending: PendingTenantDelete[] = data.tenant_ids.map((id, i) => ({
        id,
        company_name: data.company_names[i] ?? "",
        task_id: data.task_id,
      }));
      onAccepted({ pending });
    },
    onError: (e: unknown) => {
      setErr(e instanceof Error ? e.message : "Delete failed.");
    },
  });

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-stone-900/50 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          onCancel();
        }
      }}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-stone-200 bg-white p-6 shadow-xl"
        role="dialog"
        aria-labelledby="bulk-delete-tenants-title"
        aria-modal="true"
      >
        <h2 id="bulk-delete-tenants-title" className="text-lg font-semibold text-stone-900">
          Delete {sorted.length} workspace{sorted.length === 1 ? "" : "s"} permanently
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-stone-700">
          Same irreversible wipe as single-workspace delete (all tenant data). User accounts stay unless
          you remove them separately on Users. Deletion runs in the background — you can keep using the
          admin while it finishes.
        </p>
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          <p className="font-medium">Companies to delete (exact order for the text box below):</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 font-mono text-xs">
            {sorted.map((t) => (
              <li key={t.id}>{t.company_name}</li>
            ))}
          </ol>
        </div>
        <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-800">
          <ol className="list-decimal space-y-1 pl-5">
            <li>
              Type each company name on its <strong>own line</strong>, in the order above (no extra
              lines).
            </li>
            <li>
              Type the phrase{" "}
              <span className="font-mono font-semibold">{HARD_DELETE_TENANT_CONFIRMATION_PHRASE}</span>{" "}
              (case-sensitive) in the second field.
            </li>
          </ol>
        </div>
        {err ? (
          <p className="mt-3 text-sm text-red-700" role="alert">
            {err}
          </p>
        ) : null}
        <label className="mt-4 block text-sm font-medium text-stone-800">
          Company names (one per line)
          <textarea
            value={linesConfirm}
            onChange={(e) => setLinesConfirm(e.target.value)}
            rows={Math.min(12, Math.max(3, sorted.length + 1))}
            className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 font-mono text-sm"
            autoComplete="off"
            placeholder={expectedLines.join("\n")}
          />
        </label>
        <label className="mt-3 block text-sm font-medium text-stone-800">
          Confirmation phrase
          <input
            type="text"
            value={phraseConfirm}
            onChange={(e) => setPhraseConfirm(e.target.value)}
            className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 font-mono text-sm"
            autoComplete="off"
            placeholder={HARD_DELETE_TENANT_CONFIRMATION_PHRASE}
          />
        </label>
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
            onClick={onCancel}
            disabled={deleteMut.isPending}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canSubmit || deleteMut.isPending}
            onClick={() => deleteMut.mutate()}
          >
            {deleteMut.isPending ? "Starting…" : `Delete ${sorted.length} workspace(s) forever`}
          </button>
        </div>
      </div>
    </div>
  );
}
