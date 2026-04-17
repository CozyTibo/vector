import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE } from "./adminConstants";

type Props = {
  userId: string;
  email: string;
  /** Called after the server deletes the user (modal closes). */
  onDeleted?: (info: { email: string }) => void;
};

export default function AdminUserHardDelete({ userId, email, onDeleted }: Props) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [emailConfirm, setEmailConfirm] = useState("");
  const [phraseConfirm, setPhraseConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setEmailConfirm("");
      setPhraseConfirm("");
      setErr(null);
    }
  }, [open]);

  const deleteMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/users/${userId}/hard-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confirmation: phraseConfirm.trim(),
          email_confirmation: emailConfirm.trim(),
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
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
      setOpen(false);
      onDeleted?.({ email });
    },
    onError: (e: unknown) => {
      setErr(e instanceof Error ? e.message : "Delete failed.");
    },
  });

  const canSubmit =
    emailConfirm.trim() === email.trim() && phraseConfirm === HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE;

  return (
    <>
      <button
        type="button"
        className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-900 hover:bg-red-100 disabled:opacity-50"
        disabled={deleteMut.isPending}
        onClick={() => setOpen(true)}
      >
        Delete account…
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
            aria-labelledby="admin-delete-user-title"
            aria-modal="true"
          >
            <h2 id="admin-delete-user-title" className="text-lg font-semibold text-stone-900">
              Delete user account permanently
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">
              Only available when the user is not in any workspace and has no connector rows. Removes the
              account, OAuth identities, and related rows (e.g. onboarding messages) tied to this user.
            </p>
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              <ol className="list-decimal space-y-1 pl-5">
                <li>
                  Type the email exactly: <span className="font-mono">{email}</span>
                </li>
                <li>
                  Type the phrase{" "}
                  <span className="font-mono font-semibold">{HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE}</span>{" "}
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
              Email
              <input
                type="email"
                value={emailConfirm}
                onChange={(e) => setEmailConfirm(e.target.value)}
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm"
                autoComplete="off"
                placeholder={email}
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
                placeholder={HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE}
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
                {deleteMut.isPending ? "Deleting…" : "Delete user forever"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
