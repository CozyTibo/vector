# ADR-004: Ai At Ambiguity Boundaries

- Status: Accepted
- Date: 2026-05-07

## Context
Deterministic systems should own infrastructure truth while AI handles interpretation where rules are insufficient.

## Decision
AI is invoked only for bounded ambiguity, synthesis, and semantic linking.

## Alternatives Considered
- Defer decision until later implementation phase.
- Use AI-first interpretation pipeline.
- Use source-specific logic as the primary model.

## Consequences
### Positive
- Strong architecture coherence from day one.
- Lower strategic drift risk.
- Clear implementation constraints for contributors.

### Negative
- Requires disciplined schema and version management.
- Slower short-term prototyping velocity in some areas.

### Follow-Up
- Validate this ADR against phase-specific technical decisions as implementation planning deepens.
