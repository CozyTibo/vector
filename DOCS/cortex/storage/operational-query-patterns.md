# Operational Query Patterns

## Objective
Define production operator query patterns that must remain usable under stress conditions.

## Operator Query Families
- ingestion/replay pipeline health diagnostics,
- replay divergence and gap inspection,
- provenance chain debugging,
- timeline reconstruction during incidents,
- ambiguity/corruption triage workflows.

## Priority Order
1. incident and trust-critical diagnostic queries,
2. replay orchestration/control queries,
3. governance/QA validation queries,
4. exploratory analysis queries.

## Performance Requirement
Operator workflows must complete within bounded human-response windows; query latency is an operational reliability requirement, not an analytics nicety.

## Design Implication
Query optimization should prioritize trust recovery and incident response first, then broader cognition retrieval.
