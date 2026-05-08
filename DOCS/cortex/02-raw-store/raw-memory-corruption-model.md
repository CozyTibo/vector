# Raw Memory Corruption Model

## Corruption Classes
- payload mutation corruption,
- provenance discontinuity corruption,
- replay lineage corruption,
- archival pointer corruption,
- chronology/index corruption.

## Detection Signals
- payload hash mismatch,
- orphan provenance/source refs,
- replay scope gaps unexplained by policy,
- archive retrieval checksum mismatch,
- chronology scan inconsistencies.

## Failure Representation Rules
Corruption/failure states must be represented explicitly in operator-visible state:
- corruption class,
- affected scope,
- trust impact (replay-safe / degraded / unverifiable),
- recovery status.

## Containment Policy
- isolate affected tenant/connector/time scopes,
- halt replay publication for corrupted scopes,
- preserve forensic metadata for reconstruction.

## Escalation
- critical corruption triggers immediate replay trust downgrade and operator escalation.

## Boundary Reminder
Corruption handling in Phase 02 protects evidence continuity.
It does not infer missing semantic truth.
