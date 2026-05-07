# Replay Control Model

## Control Objectives
- safe replay trigger and scope selection,
- clear blast radius visibility,
- deterministic progress tracking,
- governed approval for dangerous replay scopes.

## Replay Controls
- trigger replay by:
  - tenant,
  - connector,
  - object scope,
  - time window,
  - phase range.
- replay preview:
  - expected object counts,
  - expected affected phases,
  - expected runtime/cost.

## Replay Safety
- replay lane isolation from live operations.
- no direct live cursor mutation without explicit replacement mode.
- rollback semantics require superseding-state publication controls.

## Operator Visibility
- replay state, progress, lag, failures, divergence summary,
- trust verdict and unresolved anomalies.

## Approval Model
- tenant-wide or multi-phase replay requires elevated approval and audit annotation.
