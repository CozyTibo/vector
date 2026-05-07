# Implementation Order

## Gate-Driven Sequence
1. Connector envelope contracts and ingestion validation.
2. Immutable raw event store + replay indexes.
3. Canonical contracts and deterministic mapping.
4. Entity resolution with confidence semantics.
5. Temporal graph relation construction.
6. Memory derivation and compaction layers.
7. Temporal and causal reasoning artifacts.
8. Retrieval orchestration and context-pack policy.
9. Synthesis contracts and explainability formatting.
10. Admin controls and governance hardening.

## Advance Criteria Per Phase
- Conceptual readiness signed off.
- Schema contract frozen for initial implementation slice.
- Replay behavior documented and testable.
- Failure handling policy documented.
- Upstream dependency readiness validated.

## Do-Not-Start Rules
- Do not start graph implementation before entity confidence strategy is stable.
- Do not start synthesis implementation before provenance and confidence contracts are stable.
- Do not start broad AI integration before extraction boundary policies are adopted.
