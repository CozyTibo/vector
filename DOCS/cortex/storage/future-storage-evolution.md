# Future Storage Evolution

## Objective
Define realistic evolution paths without forcing premature multi-system architecture.

## Candidate Paths
- Postgres-only with disciplined optimization,
- Postgres + pgvector for semantic candidate retrieval,
- Postgres + OpenSearch for text/provenance search acceleration,
- Postgres + lineage-focused graph-style acceleration,
- dedicated replay acceleration path for large replay economics pressure.

## Evaluation Dimensions
- impact on deterministic replay guarantees,
- provenance consistency and explainability,
- operational complexity and staffing burden,
- migration/cutover and rollback safety.

## Evolution Rules
- additional systems require threshold-driven justification,
- source-of-truth integrity remains in primary governed store,
- each added subsystem must include integrity validation playbook.

## Conclusion
Evolution is expected; uncontrolled architecture sprawl is not.
