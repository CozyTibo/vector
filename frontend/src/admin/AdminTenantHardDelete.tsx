import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { HARD_DELETE_TENANT_CONFIRMATION_PHRASE } from "./adminConstants";

type Props = {
  tenantId: string;
  companyName: string;
  /** Tighter chrome for dashboard grids (workspace tab). */
  compact?: boolean;
};

export default function AdminTenantHardDelete({ tenantId, companyName, compact = false }: Props) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [companyConfirm, setCompanyConfirm] = useState("");
  const [phraseConfirm, setPhraseConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setCompanyConfirm("");
      setPhraseConfirm("");
      setErr(null);
    }
  }, [open]);

  const deleteMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/hard-delete`, {
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
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin-tenants"] });
      navigate("/admin", {
        state: {
          adminFlash: {
            kind: "success" as const,
            text: `Workspace “${companyName}” was permanently deleted.`,
          },
        },
      });
    },
    onError: (e: unknown) => {
      setErr(e instanceof Error ? e.message : "Delete failed.");
    },
  });

  const canSubmit =
    companyConfirm.trim() === companyName.trim() && phraseConfirm === HARD_DELETE_TENANT_CONFIRMATION_PHRASE;

  return (
    <section
      className={
        compact
          ? "rounded-lg border border-red-200 bg-red-50/50 p-3 shadow-sm"
          : "rounded-xl border border-red-200 bg-red-50/40 p-6 shadow-sm"
      }
    >
      <h2 className={compact ? "text-sm font-semibold text-red-950" : "text-base font-semibold text-red-950"}>
        Delete this company
      </h2>
      <p
        className={
          compact
            ? "mt-1 text-[11px] leading-snug text-red-900/90"
            : "mt-2 text-sm leading-relaxed text-red-900/90"
        }
      >
        {compact ? (
          <>
            Removes <strong>all</strong> workspace data (irreversible). Accounts stay; membership here is
            removed.
          </>
        ) : (
          <>
            Permanently remove this workspace and <strong>all</strong> related data (connectors, onboarding,
            Slack sessions, manager-insight state). User accounts are kept but lose
            membership here. This cannot be undone.
          </>
        )}
      </p>
      <button
        type="button"
        className={
          compact
            ? "mt-2 rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-800 shadow-sm hover:bg-red-50 disabled:opacity-50"
            : "mt-4 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 shadow-sm hover:bg-red-50 disabled:opacity-50"
        }
        disabled={deleteMut.isPending}
        onClick={() => setOpen(true)}
      >
        Delete company…
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-stone-900/50 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setOpen(false);
            }
          }}
        >
          <div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-stone-200 bg-white p-6 shadow-xl"
            role="dialog"
            aria-labelledby="ws-delete-tenant-title"
            aria-modal="true"
          >
            <h2 id="ws-delete-tenant-title" className="text-lg font-semibold text-stone-900">
              Delete company permanently
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              This removes <span className="font-semibold">{companyName}</span> and all tenant-scoped
              data. Confirm in two steps below.
            </p>
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              <ol className="list-decimal space-y-1 pl-5">
                <li>
                  Type the company name exactly: <span className="font-mono">{companyName}</span>
                </li>
                <li>
                  Type the phrase{" "}
                  <span className="font-mono font-semibold">{HARD_DELETE_TENANT_CONFIRMATION_PHRASE}</span>{" "}
                  (case-sensitive)
                </li>
              </ol>
            </div>
            {err ? (
              <p className="mt-3 text-sm text-red-700" role="alert">
                {err}
              </p>
            ) : null}
            <label className="mt-4 block text-sm font-medium text-stone-800">
              Company name
              <input
                type="text"
                value={companyConfirm}
                onChange={(e) => setCompanyConfirm(e.target.value)}
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
                autoComplete="off"
                placeholder={companyName}
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
                onClick={() => setOpen(false)}
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
                {deleteMut.isPending ? "Deleting…" : "Delete company forever"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
