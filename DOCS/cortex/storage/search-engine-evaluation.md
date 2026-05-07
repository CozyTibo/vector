# Search Engine Evaluation

## Objective
Evaluate where dedicated search/index engines improve cognition queryability while preserving deterministic reconstruction.

## Candidate Value Areas
- full-text evidence search,
- fuzzy or semantic prefiltering for provenance/lineage discovery,
- operational triage search across large historical evidence sets.

## Candidate Systems
- OpenSearch/Elasticsearch for text and facet-heavy filtering,
- pgvector for semantic candidate retrieval assistance.

## Risks
- eventual consistency drift from primary source-of-truth,
- indexing pipeline complexity and failure modes,
- replay-triggered index rebuild costs.

## Safe Adoption Model
- treat search systems as acceleration indexes only,
- never treat search index as authoritative lineage source,
- enforce replay-based rebuild path for consistency recovery.
