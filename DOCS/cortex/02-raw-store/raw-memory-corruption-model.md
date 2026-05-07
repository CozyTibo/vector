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

## Containment Policy
- isolate affected tenant/connector/time scopes,
- halt replay publication for corrupted scopes,
- preserve forensic metadata for reconstruction.

## Escalation
- critical corruption triggers immediate replay trust downgrade and operator escalation.
