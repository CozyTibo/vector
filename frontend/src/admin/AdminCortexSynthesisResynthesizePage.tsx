import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type WorkflowsCatalog = {
  dangerous_actions: {
    action_id: string;
    confirmation_phrase: string;
  }[];
};

export default function AdminCortexSynthesisResynthesizePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [phrase, setPhrase] = useState("");
  const [envelopeJson, setEnvelopeJson] = useState(
    JSON.stringify(
      {
        synthesis_workload_class: "degradation_brief",
        synthesis_intent: "prove",
        execution_partition: "authoritative",
        retrieval_scope: {},
      },
      null,
      2,
    ),
  );

  const workflows = useQuery({
    queryKey: ["synthesis-workflows", tenantId],
    queryFn: () =>
      adminJson<WorkflowsCatalog>(`/admin/tenants/${tenantId}/cortex/synthesis/workflows`),
  });

  const expectedPhrase =
    workflows.data?.dangerous_actions.find((a) => a.action_id === "resynthesize")
      ?.confirmation_phrase ?? "";

  const resynthMut = useMutation({
    mutationFn: async () => {
      let envelope: Record<string, unknown>;
      try {
        envelope = JSON.parse(envelopeJson) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid envelope JSON");
      }
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/synthesis/jobs/resynthesize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation_phrase: phrase, envelope }),
        },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
  });

  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-amber-950">Force re-synthesis (W3)</h2>
      <p className="mt-1 text-sm text-amber-900">
        Dangerous — requires exact confirmation phrase for this tenant.
      </p>
      {expectedPhrase && (
        <p className="mt-2 font-mono text-xs text-amber-950">Expected: {expectedPhrase}</p>
      )}
      <label className="mt-4 block text-sm">
        Confirmation phrase
        <input
          className="mt-1 w-full rounded border border-stone-300 px-2 py-1 font-mono text-sm"
          value={phrase}
          onChange={(e) => setPhrase(e.target.value)}
        />
      </label>
      <label className="mt-3 block text-sm">
        Job envelope JSON
        <textarea
          className="mt-1 w-full rounded border border-stone-300 p-2 font-mono text-xs"
          rows={10}
          value={envelopeJson}
          onChange={(e) => setEnvelopeJson(e.target.value)}
        />
      </label>
      <button
        type="button"
        className="mt-3 rounded bg-amber-800 px-3 py-1.5 text-sm text-white disabled:opacity-50"
        disabled={resynthMut.isPending}
        onClick={() => resynthMut.mutate()}
      >
        {resynthMut.isPending ? "Running…" : "RE-SYNTHESIZE"}
      </button>
      {resynthMut.error && (
        <p className="mt-2 text-sm text-red-700">{(resynthMut.error as Error).message}</p>
      )}
      {resynthMut.data && (
        <pre className="mt-3 max-h-64 overflow-auto rounded border border-stone-200 bg-white p-2 text-xs">
          {JSON.stringify(resynthMut.data, null, 2)}
        </pre>
      )}
    </section>
  );
}
