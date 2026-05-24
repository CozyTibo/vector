type LineageChain = {
  nodes?: Record<string, unknown>[];
  edges?: Record<string, unknown>[];
  terminal?: Record<string, unknown>;
};

function nodeLabel(node: Record<string, unknown>): string {
  const kind = String(node.artifact_kind ?? node.kind ?? "node");
  const ref = String(node.artifact_ref ?? node.ref ?? node.id ?? "—");
  return `${kind} · ${ref}`;
}

export function LineageChainPanel({ chain }: { chain: Record<string, unknown> }) {
  const payload = (chain.chain ?? chain) as LineageChain;
  const nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const edges = Array.isArray(payload.edges) ? payload.edges : [];
  const explain = chain.explainability as Record<string, unknown> | undefined;

  if (nodes.length === 0 && edges.length === 0) {
    return (
      <p className="text-sm text-stone-500">
        No lineage hops resolved for this terminal artifact.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {explain?.summary ? (
        <p className="text-sm text-stone-700">{String(explain.summary)}</p>
      ) : null}
      <ol className="space-y-3 border-l-2 border-indigo-200 pl-4">
        {nodes.map((node, idx) => (
          <li key={`${String(node.artifact_kind ?? idx)}-${String(node.artifact_ref ?? idx)}`}>
            <p className="text-sm font-medium text-stone-900">{nodeLabel(node)}</p>
            {node.omission_summary ? (
              <p className="mt-1 text-xs text-amber-800">Omission: {JSON.stringify(node.omission_summary)}</p>
            ) : null}
          </li>
        ))}
      </ol>
      {edges.length > 0 ? (
        <details className="text-xs text-stone-600">
          <summary className="cursor-pointer text-indigo-700">{edges.length} edge records</summary>
          <pre className="mt-2 overflow-x-auto rounded bg-stone-50 p-2">{JSON.stringify(edges, null, 2)}</pre>
        </details>
      ) : null}
      {chain.truncated ? (
        <p className="text-xs text-amber-800">Lineage truncated at max hop limit.</p>
      ) : null}
    </div>
  );
}
