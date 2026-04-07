import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type TenantRow = {
  id: string;
  company_name: string;
  created_at: string;
  onboarding_status: string | null;
  onboarding_current_step: string | null;
  connected_connectors: string[];
};

/** Must match backend ``HARD_DELETE_TENANT_CONFIRMATION_PHRASE`` exactly. */
const HARD_DELETE_CONFIRM_PHRASE = "DELETE TENANT AND ALL DATA";

export default function AdminTenantsPage() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => adminJson<{ items: TenantRow[] }>("/admin/tenants"),
  });

  const [deleteTarget, setDeleteTarget] = useState<TenantRow | null>(null);
  const [companyConfirm, setCompanyConfirm] = useState("");
  const [phraseConfirm, setPhraseConfirm] = useState("");
  const [flash, setFlash] = useState<{ kind: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    if (deleteTarget) {
      setCompanyConfirm("");
      setPhraseConfirm("");
    }
  }, [deleteTarget]);

  useEffect(() => {
    if (flash?.kind !== "success") {
      return;
    }
    const id = window.setTimeout(() => setFlash(null), 6500);
    return () => window.clearTimeout(id);
  }, [flash]);

  const deleteMut = useMutation({
    mutationFn: async (t: TenantRow) => {
      const res = await adminFetch(`/admin/tenants/${t.id}/hard-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confirmation: phraseConfirm.trim(),
          company_name_confirmation: companyConfirm.trim(),
        }),
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<unknown>;
    },
    onSuccess: async (_, t) => {
      setFlash({
        kind: "success",
        message: `Tenant “${t.company_name}” was permanently deleted.`,
      });
      setDeleteTarget(null);
      await qc.invalidateQueries({ queryKey: ["admin-tenants"] });
    },
    onError: (e: unknown) => {
      setFlash({
        kind: "error",
        message: e instanceof Error ? e.message : "Delete failed.",
      });
    },
  });

  const canSubmitDelete =
    Boolean(deleteTarget) &&
    companyConfirm.trim() === deleteTarget?.company_name.trim() &&
    phraseConfirm === HARD_DELETE_CONFIRM_PHRASE;

  return (
    <main className="relative mx-auto max-w-5xl px-4 py-8">
      {flash ? (
        <div
          className={
            "fixed left-1/2 top-4 z-[60] flex max-w-md -translate-x-1/2 items-start gap-3 rounded-lg border px-4 py-3 shadow-lg " +
            (flash.kind === "success"
              ? "border-emerald-300 bg-emerald-50 text-emerald-950"
              : "border-red-300 bg-red-50 text-red-950")
          }
          role={flash.kind === "error" ? "alert" : "status"}
          aria-live={flash.kind === "error" ? "assertive" : "polite"}
        >
          <p className="min-w-0 flex-1 text-sm font-medium leading-snug">{flash.message}</p>
          <button
            type="button"
            className={
              "shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold " +
              (flash.kind === "success"
                ? "text-emerald-800 hover:bg-emerald-200/60"
                : "text-red-800 hover:bg-red-200/60")
            }
            onClick={() => setFlash(null)}
          >
            Dismiss
          </button>
        </div>
      ) : null}
      <h1 className="mb-6 text-xl font-semibold text-stone-900">Tenants</h1>
      {q.isPending ? <p className="text-sm text-stone-600">Loading…</p> : null}
      {q.isError ? (
        <p className="text-sm text-red-700">{(q.error as Error).message}</p>
      ) : null}
      {q.data ? (
        <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
          <table className="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Onboarding</th>
                <th>Connectors</th>
                <th>ID</th>
                <th>Created</th>
                <th className="w-28">Actions</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-stone-500">
                    No tenants
                  </td>
                </tr>
              ) : (
                q.data.items.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <Link
                        to={`/admin/tenants/${t.id}/overview`}
                        className="font-medium text-blue-700 underline"
                      >
                        {t.company_name}
                      </Link>
                    </td>
                    <td className="text-sm text-stone-700">
                      {t.onboarding_status ?? "—"}
                      {t.onboarding_current_step ? (
                        <span className="block text-xs text-stone-500">{t.onboarding_current_step}</span>
                      ) : null}
                    </td>
                    <td className="text-sm text-stone-700">
                      {t.connected_connectors.length ? t.connected_connectors.join(", ") : "—"}
                    </td>
                    <td className="font-mono text-xs text-stone-600">{t.id}</td>
                    <td className="text-sm text-stone-700">
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="text-sm font-medium text-red-700 underline decoration-red-300 hover:text-red-900"
                        onClick={() => setDeleteTarget(t)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : null}

      {deleteTarget ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/50 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setDeleteTarget(null);
            }
          }}
        >
          <div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-stone-200 bg-white p-6 shadow-xl"
            role="dialog"
            aria-labelledby="delete-tenant-title"
            aria-modal="true"
          >
            <h2 id="delete-tenant-title" className="text-lg font-semibold text-stone-900">
              Delete tenant permanently
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              This removes the tenant <span className="font-semibold">{deleteTarget.company_name}</span> and{" "}
              <strong>all</strong> related data: connectors, OAuth links, onboarding, raw ingestion,
              projections, and canonical graph. User accounts are kept, but lose membership to this
              workspace. This cannot be undone.
            </p>
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              <p className="font-medium">Confirm in two steps:</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5">
                <li>
                  Type the <span className="font-mono font-semibold">company name</span> exactly:{" "}
                  <span className="font-mono">{deleteTarget.company_name}</span>
                </li>
                <li>
                  Type the phrase{" "}
                  <span className="font-mono font-semibold">{HARD_DELETE_CONFIRM_PHRASE}</span>{" "}
                  (case-sensitive)
                </li>
              </ol>
            </div>
            <label className="mt-4 block text-sm font-medium text-stone-800">
              Company name
              <input
                type="text"
                value={companyConfirm}
                onChange={(e) => setCompanyConfirm(e.target.value)}
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
                autoComplete="off"
                placeholder={deleteTarget.company_name}
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
                placeholder={HARD_DELETE_CONFIRM_PHRASE}
              />
            </label>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
                onClick={() => setDeleteTarget(null)}
                disabled={deleteMut.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!canSubmitDelete || deleteMut.isPending}
                onClick={() => deleteMut.mutate(deleteTarget)}
              >
                {deleteMut.isPending ? "Deleting…" : "Delete tenant forever"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
