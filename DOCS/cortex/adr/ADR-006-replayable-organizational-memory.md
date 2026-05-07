# ADR-006: Replayable Organizational Memory

- Status: Accepted
- Date: 2026-05-07

## Context
Evolving schemas/processors require deterministic regeneration and comparability across historical states.

## Decision
Cortex must support full and partial replay across all memory layers.

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
