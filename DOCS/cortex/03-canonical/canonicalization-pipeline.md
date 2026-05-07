# Canonicalization Pipeline

## Stage Sequence
1. Raw retrieval by deterministic scope.
2. Structural normalization of source payload shape.
3. Deterministic extraction of explicit semantics.
4. AI-assisted extraction for approved ambiguity boundaries.
5. Ontology mapping and concept construction.
6. Ambiguity/conflict registration.
7. Provenance + temporal propagation attachment.
8. Canonical persistence and downstream emission.

## Ordering Guarantees
- per replay/run scope: deterministic processing order by source chronology rules.
- no global cross-connector strict order requirement.

## Failure Semantics
- deterministic extraction failures can quarantine affected records.
- AI extraction failures degrade gracefully to unresolved ambiguity.
- provenance or temporal propagation failure is a blocking error.

## Replay Guarantees
- pipeline must be reproducible for fixed input and versions.
- divergence must be attributable to version differences.

## Idempotency Assumptions
- canonicalization uses deterministic canonical id generation and version-aware dedupe keys.
