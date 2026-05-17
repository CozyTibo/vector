import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type RemediationLink = {
  retrieval_omission_class: string;
  spa_route: string;
  hint: string;
};

export default function AdminCortexRetrievalQueryPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/retrieval`;
  const [bodyText, setBodyText] = useState(
    JSON.stringify(
      {
        workload_class: "resolve",
        intent_class: "explain_evidence",
        temporal_scope: { t_as_of: "2020-01-01T00:00:00Z" },
        selection_policy: { max_hits: 10 },
      },
      null,
      2,
    ),
  );

  const contractQ = useQuery({
    queryKey: ["retrieval-query-contract", tenantId],
    queryFn: () =>
      adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/retrieval/query-contract`,
      ),
  });

  const runMutation = useMutation({
    mutationFn: async () => {
      const parsed = JSON.parse(bodyText) as Record<string, unknown>;
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/retrieval/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<Record<string, unknown> & { remediation_links?: RemediationLink[] }>;
    },
  });

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Query debugger (W1)</h2>
        <p className="mt-1 text-sm text-stone-600">
          POST lawful retrieval query envelope — RESOLVE phase with guided remediation on omissions.
        </p>
        <textarea
          className="mt-3 w-full rounded border border-stone-300 font-mono text-xs"
          rows={14}
          value={bodyText}
          onChange={(e) => setBodyText(e.target.value)}
        />
        <button
          type="button"
          className="mt-2 rounded bg-violet-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-800"
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
        >
          {runMutation.isPending ? "Running…" : "Execute query"}
        </button>
        {runMutation.error && (
          <p className="mt-2 text-sm text-red-700">Query failed — check envelope and legality.</p>
        )}
        {runMutation.data?.remediation_links && runMutation.data.remediation_links.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm">
            {runMutation.data.remediation_links.map((link) => (
              <li key={link.retrieval_omission_class}>
                <code className="text-xs">{link.retrieval_omission_class}</code>
                {": "}
                <Link className="text-violet-700 underline" to={`${base}/${link.spa_route}`}>
                  {link.spa_route}
                </Link>
                <span className="text-stone-600"> — {link.hint}</span>
              </li>
            ))}
          </ul>
        )}
        {runMutation.data && (
          <pre className="mt-3 max-h-[24rem] overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-xs">
            {JSON.stringify(runMutation.data, null, 2)}
          </pre>
        )}
      </section>
      {contractQ.data && (
        <section className="rounded-lg border border-stone-200 bg-stone-50 p-3 text-xs">
          <h3 className="font-medium text-stone-800">Query contract</h3>
          <pre className="mt-2 max-h-48 overflow-auto">{JSON.stringify(contractQ.data, null, 2)}</pre>
        </section>
      )}
    </div>
  );
}
