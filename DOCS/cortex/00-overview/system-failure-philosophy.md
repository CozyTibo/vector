# System Failure Philosophy

## Failure Stance
Cortex prioritizes truthful partial output over fabricated completeness.

## Failure Classes
- Connector desynchronization or missing windows.
- Partial ingestion persistence failures.
- Canonical mapping mismatches after schema evolution.
- Low-confidence entity links.
- Inference disagreement or conflicting evidence.
- Replay inconsistency between processor versions.

## Degradation Rules
- Preserve valid deterministic artifacts even when inference fails.
- Emit unresolved ambiguity markers instead of speculative closures.
- Quarantine malformed artifacts with operator-visible diagnostics.
- Prevent downstream synthesis from claiming certainty above evidence.

## Recovery Rules
- Use replay for deterministic reconstruction.
- Keep failure lineage and remediation actions auditable.
- Avoid silent corrections; represent corrections as new versioned artifacts.
