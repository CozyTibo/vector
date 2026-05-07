# Corruption Detection Model

## Detectable Corruption Classes
- replay corruption,
- checkpoint corruption,
- duplicate persistence corruption,
- payload mutation corruption,
- provenance discontinuity,
- missing replay coverage,
- cursor inconsistency,
- ordering corruption.

## Detection Signals
- checksum/hash mismatch for immutable payload rows.
- duplicate idempotency key existence >1.
- checkpoint monotonicity violations.
- provenance null/missing required refs.
- replay completeness gaps (scope expected vs persisted coverage).
- cursor anomalies (invalid jump, inconsistent token lineage).
- ordering anomaly rates exceeding threshold.

## Operator Visibility
- corruption class severity labels,
- affected tenant/connector/scope identifiers,
- first detected timestamp and suspected blast radius,
- recommended containment path.

## Escalation Expectations
- critical classes (payload mutation, provenance discontinuity, replay corruption) trigger immediate escalation.
- medium classes (ordering drift, replay gap) trigger bounded remediation with incident tracking.

## Containment Expectations
- freeze affected replay publication when trust is uncertain.
- isolate affected connector or scope.
- preserve forensic data for deterministic reconstruction.
