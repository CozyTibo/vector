import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE } from "./adminConstants";
import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

export default function AdminCortexRetrievalIndexPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [phrase, setPhrase] = useState("");

  const indexQ = useQuery({
    queryKey: ["retrieval-index", tenantId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(`/admin/tenants/${tenantId}/cortex/retrieval/index`),
  });

  const rebuildMutation = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/retrieval/index/rebuild`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation_phrase: phrase }),
        },
      );
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["retrieval-index", tenantId] });
    },
  });

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Index materialization</h2>
        {indexQ.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {indexQ.data && (
          <pre className="mt-3 max-h-[20rem] overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-xs">
            {JSON.stringify(indexQ.data, null, 2)}
          </pre>
        )}
      </section>

      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
        <h3 className="font-semibold text-amber-900">Dangerous: index rebuild (W3)</h3>
        <p className="mt-1 text-sm text-amber-800">
          Type exactly: <code className="text-xs">{RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE}</code>
        </p>
        <input
          className="mt-2 w-full rounded border border-amber-300 px-2 py-1 font-mono text-sm"
          value={phrase}
          onChange={(e) => setPhrase(e.target.value)}
          placeholder={RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE}
        />
        <button
          type="button"
          className="mt-2 rounded bg-amber-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-900 disabled:opacity-50"
          disabled={
            phrase !== RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE || rebuildMutation.isPending
          }
          onClick={() => rebuildMutation.mutate()}
        >
          {rebuildMutation.isPending ? "Rebuilding…" : "Execute rebuild"}
        </button>
        {rebuildMutation.error && (
          <p className="mt-2 text-sm text-red-700">{String(rebuildMutation.error.message)}</p>
        )}
        {rebuildMutation.data && (
          <pre className="mt-3 max-h-48 overflow-auto rounded border border-stone-200 bg-white p-3 text-xs">
            {JSON.stringify(rebuildMutation.data, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}
