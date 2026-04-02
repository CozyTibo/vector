import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../lib/adminFetch";
import { getAdminPassword } from "../lib/adminCredentials";
import { adminCanonicalClient, readErrorDetail } from "../lib/canonicalApi";
import CanonicalDebugPage from "../pages/debug/CanonicalDebugPage";

/** Must match ``STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE`` in ``step2_step3_reset.py`` (case-sensitive). */
const STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE = "DELETE ALL STEP3 CANONICAL DATA";

export default function AdminTenantStep3() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const pw = getAdminPassword();

  const [resetOpen, setResetOpen] = useState(false);
  const [resetPhrase, setResetPhrase] = useState("");
  const [resetPending, setResetPending] = useState(false);
  const [resetErr, setResetErr] = useState<string | null>(null);
  const [resetOk, setResetOk] = useState<string | null>(null);
  const resetPhraseOk = resetPhrase === STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE;

  const runStep3Reset = async () => {
    if (!resetPhraseOk || !tenantId) return;
    setResetPending(true);
    setResetErr(null);
    setResetOk(null);
    try {
      const res = await adminFetch(`/admin/tenants/${tenantId}/canonical/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE }),
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      const body = (await res.json()) as {
        deleted_relationships: number;
        deleted_mapping_events: number;
        deleted_current_mappings: number;
        deleted_external_references: number;
        deleted_actor_external_identities: number;
        deleted_artifacts: number;
        deleted_actors: number;
        deleted_step3_canonical_cursors: number;
      };
      setResetOk(
        `Removed relationships ${body.deleted_relationships}; artifacts ${body.deleted_artifacts}; actors ${body.deleted_actors}; cursors ${body.deleted_step3_canonical_cursors}.`,
      );
      setResetOpen(false);
      setResetPhrase("");
      const cqTag = `admin:${tenantId}`;
      void qc.invalidateQueries({
        predicate: (q) => Array.isArray(q.queryKey) && q.queryKey.includes(cqTag),
      });
    } catch (e) {
      setResetErr((e as Error).message);
    } finally {
      setResetPending(false);
    }
  };

  if (!tenantId) {
    return <p className="text-sm text-red-700">Missing tenant</p>;
  }
  if (!pw) {
    return <p className="text-sm text-red-700">Admin session missing.</p>;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50/50 px-3 py-2">
        <button
          type="button"
          className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-900 hover:bg-red-100 disabled:opacity-40"
          disabled={resetPending}
          onClick={() => {
            setResetOpen(true);
            setResetPhrase("");
            setResetErr(null);
            setResetOk(null);
          }}
        >
          Reset Step 3 canonical data…
        </button>
        {resetOk ? <span className="text-sm text-emerald-800">{resetOk}</span> : null}
        {resetErr ? <span className="text-sm text-red-700">{resetErr}</span> : null}
      </div>
      {resetOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="step3-reset-title"
        >
          <div className="max-w-lg rounded-lg border border-stone-200 bg-white p-5 shadow-lg">
            <h2 id="step3-reset-title" className="text-lg font-semibold text-stone-900">
              Reset all Step 3 canonical data for this tenant?
            </h2>
            <p className="mt-2 text-sm text-stone-700">
              This removes <strong>actors</strong>, <strong>artifacts</strong>, <strong>relationships</strong>,{" "}
              <strong>external references</strong>, <strong>mappings</strong>, and{" "}
              <strong>step3_canonical_cursor</strong> rows for this workspace (all connections). Step 1
              raw and Step 2 projections are <strong>not</strong> deleted.
            </p>
            <p className="mt-3 text-sm font-medium text-stone-800">
              Type the phrase below exactly (case-sensitive) to enable reset:
            </p>
            <code className="mt-1 block rounded bg-stone-100 px-2 py-1.5 text-xs text-stone-800">
              {STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE}
            </code>
            <input
              type="text"
              className="mt-3 w-full rounded border border-stone-300 px-2 py-1.5 text-sm"
              placeholder="Type confirmation phrase…"
              value={resetPhrase}
              onChange={(e) => setResetPhrase(e.target.value)}
              autoComplete="off"
              autoFocus
            />
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm hover:bg-stone-50"
                disabled={resetPending}
                onClick={() => {
                  setResetOpen(false);
                  setResetPhrase("");
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded border border-red-600 bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-40"
                disabled={!resetPhraseOk || resetPending}
                onClick={() => void runStep3Reset()}
              >
                {resetPending ? "Resetting…" : "Reset Step 3 data"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <CanonicalDebugPage
        client={adminCanonicalClient(tenantId, pw)}
        entityBasePath={`/admin/tenants/${tenantId}/step3`}
        dashboardHref="/admin"
        visualTheme="admin"
      />
    </div>
  );
}
