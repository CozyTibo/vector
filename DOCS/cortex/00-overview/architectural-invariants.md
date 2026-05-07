# Canonical Architectural Invariants

## Non-Negotiable Invariants
1. Raw events are immutable source-faithful evidence.
2. Replay remains possible for every persistent transformation stage.
3. Provenance remains reconstructable from synthesis/inference back to raw events.
4. Connectors remain adapters; no organizational reasoning in connector layer.
5. Ingestion does not infer organizational meaning.
6. Canonical memory remains tool-agnostic and contract-driven.
7. AI never becomes source-of-truth for canonical facts.
8. Confidence and ambiguity are explicit; uncertainty is never hidden.
9. Temporal reconstruction remains possible with validity windows and supersession links.
10. Cross-tenant data leakage is an architecture failure.

## Invariant Enforcement Expectations
- Every phase document must declare forbidden logic aligned with these invariants.
- Every schema update must preserve provenance and replay semantics.
- Every inference output must include confidence and evidence references.

## Change Policy
Any proposal weakening an invariant requires:
1. ADR with explicit risk statement,
2. replay/provenance impact analysis,
3. approval before implementation planning.
