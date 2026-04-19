import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE } from "./adminConstants";

type Props = {
  tenantId: string;
  companyName: string;
};

export default function AdminTenantResetToSignup({ tenantId, companyName }: Props) {
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

  const resetMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/reset-to-fresh-signup`, {
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
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] }),
        qc.invalidateQueries({ queryKey: ["admin-connections", tenantId] }),
        qc.invalidateQueries({ queryKey: ["admin-mo-tenant-summary", tenantId] }),
        qc.invalidateQueries({ queryKey: ["admin-tenants"] }),
      ]);
      setOpen(false);
    },
    onError: (e: unknown) => {
      setErr(e instanceof Error ? e.message : "Reset failed.");
    },
  });

  const canSubmit =
    companyConfirm.trim() === companyName.trim() &&
    phraseConfirm === RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE;

  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 shadow-sm">
      <h2 className="text-sm font-semibold text-amber-950">Reset workspace to fresh signup</h2>
      <p className="mt-1 text-[11px] leading-snug text-amber-900/90">
        Wipes <strong>all</strong> tenant-scoped product data (ingestion, canonical graph, connectors,
        website onboarding, manager Slack onboarding) and turns off product access + Slack pause. Keeps
        this company id, name, and <strong>all memberships</strong> — same users, empty product state.
      </p>
      <button
        type="button"
        className="mt-2 rounded-md border border-amber-400 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 shadow-sm hover:bg-amber-50 disabled:opacity-50"
        disabled={resetMut.isPending}
        onClick={() => setOpen(true)}
      >
        Reset to fresh signup…
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
            aria-labelledby="ws-reset-tenant-title"
            aria-modal="true"
          >
            <h2 id="ws-reset-tenant-title" className="text-lg font-semibold text-stone-900">
              Reset workspace to fresh signup
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              This resets <span className="font-semibold">{companyName}</span> to an empty product state
              (like right after signup). Confirm in two steps below.
            </p>
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              <ol className="list-decimal space-y-1 pl-5">
                <li>
                  Type the company name exactly: <span className="font-mono">{companyName}</span>
                </li>
                <li>
                  Type the phrase{" "}
                  <span className="font-mono font-semibold">{RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE}</span>{" "}
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
                placeholder={RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE}
              />
            </label>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
                onClick={() => setOpen(false)}
                disabled={resetMut.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!canSubmit || resetMut.isPending}
                onClick={() => resetMut.mutate()}
              >
                {resetMut.isPending ? "Resetting…" : "Reset workspace"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
