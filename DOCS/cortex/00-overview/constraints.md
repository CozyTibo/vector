# Constraints

## Non-Negotiable Architecture Constraints
- PostgreSQL-first for all persisted Cortex layers in initial implementation.
- Immutable raw events; no update-in-place mutation of source payload truth.
- Canonical schemas are required before cross-tool reasoning.
- Replay must be possible for every persisted transformation stage.
- AI outputs are non-authoritative and must not replace deterministic facts.

## Forbidden Patterns
- Tool-specific business logic embedded in connectors.
- Prompt-only memory that bypasses persistent lineage.
- Opaque scoring without confidence semantics.
- Hidden chain-of-thought style internal reasoning used as truth artifact.
- Full-context window dependence for production behavior.

## Operational Constraints
- Expected multi-year history per tenant.
- Millions of source events with selective replay windows.
- High fanout relation growth from cross-tool linking.
- Ingestion and replay operations must coexist safely.

## Evolution Constraints
- Schema evolution must include backward read strategy or migration strategy.
- Versioned processors must remain inspectable.
- Deletion and retention policies must be represented in lifecycle controls.
