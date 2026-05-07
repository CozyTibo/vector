# Context Explosion And Memory Hierarchy

## Why Naive Full-Context Prompting Fails
- Organizational history grows faster than prompt windows and token budgets.
- Relevant context is sparse relative to total available history.
- Large unfiltered context increases contradiction surface and weakens precision.
- Repeatedly repacking raw history creates cost and latency cliffs.

## Why Organizational Memory Scales Non-Linearly
Cross-tool references create combinatorial relation growth. As teams, tools, and years increase, linkage space expands faster than event count.

## Layered Retrieval Requirement
Retrieval must operate across layered memory:
- raw memory (immutable evidence),
- canonical memory (normalized semantics),
- graph memory (relational topology),
- compressed memory (high-signal abstraction),
- derived memory (query-targeted projections),
- semantic memory (meaning-oriented retrieval aids),
- temporal memory (state evolution and lineage).

## Why Raw Retrieval Alone Is Insufficient
Raw payload retrieval cannot reliably reconstruct decision evolution, ownership transitions, or causal chains without canonical, graph, and temporal layers.

## Summarization Hierarchy Requirement
Summaries must be layered and provenance-linked:
1. local thread summary,
2. topic-level synthesis,
3. project timeline narrative,
4. initiative-level memory abstraction.
No summary may orphan evidence lineage.
