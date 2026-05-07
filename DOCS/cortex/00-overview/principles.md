# Core Principles

## Constraint Hierarchy
When principles conflict, apply this order:
1. Tenant safety and data isolation.
2. Deterministic replayability and provenance integrity.
3. Canonical consistency across tools.
4. Operational recoverability.
5. AI-assisted interpretation quality.

## Deterministic-First
Core pipeline outputs must be reproducible from immutable inputs, versioned processors, and documented schema versions. If output changes after processor updates, both versions must be comparable and explainable.

## Canonical-First
Organizational logic is forbidden on source-native payloads. Any cross-tool reasoning before canonicalization is an architecture violation because semantics are not yet normalized.

## Replayability-First
Replay is a primary system behavior, not a repair tool. Every persistent stage must support deterministic reprocessing with explicit replay scope and replay lineage.

## Explainability Over Convenience
Any derived statement must carry evidence lineage. If confidence is low or conflicting evidence exists, Cortex must emit uncertainty rather than force a single narrative.

## Connector Isolation
Connectors may fetch and normalize source events only. Connectors may not infer ownership, classify strategic risk, or build organization-level semantics.

## Temporal Integrity
Time is modeled as event-time and processing-time. Backfills, edits, and late-arriving events must preserve chronology semantics without overwriting historical truth.

## AI At Ambiguity Boundaries
AI is invoked only where deterministic extraction cannot safely resolve meaning. AI output is interpretive, confidence-scored, and always downstream of deterministic evidence capture.
