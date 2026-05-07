# ADR-003: Canonical First Architecture

- Status: Accepted
- Date: 2026-05-07

## Context
Tool-specific schemas cannot safely support cross-tool cognition; canonicalization is required for semantic coherence.

## Decision
All organizational reasoning operates on canonical models, not source-native payloads.

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
