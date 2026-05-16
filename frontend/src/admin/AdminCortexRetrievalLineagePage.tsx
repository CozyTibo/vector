import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

export default function AdminCortexRetrievalLineagePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [kind, setKind] = useState("retrieval_index");
  const [ref, setRef] = useState("");

  const { data, refetch, isFetching } = useQuery({
    queryKey: ["lineage", tenantId, kind, ref],
    enabled: false,
    queryFn: () =>
      adminJson<{ chain: unknown; explainability: unknown }>(
        `/admin/tenants/${tenantId}/cortex/retrieval/lineage/${encodeURIComponent(kind)}/${encodeURIComponent(ref)}`,
      ),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <input
          className="rounded border border-stone-300 px-2 py-1 text-sm"
          placeholder="artifact kind"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        />
        <input
          className="min-w-[200px] flex-1 rounded border border-stone-300 px-2 py-1 text-sm"
          placeholder="artifact ref"
          value={ref}
          onChange={(e) => setRef(e.target.value)}
        />
        <button
          type="button"
          className="rounded bg-violet-700 px-3 py-1 text-sm text-white"
          disabled={!ref.trim() || isFetching}
          onClick={() => refetch()}
        >
          Trace lineage
        </button>
      </div>
      {data && (
        <pre className="max-h-96 overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
