# Confidence Propagation Model

## Purpose
Define how confidence flows through identity and linkage outputs.

## Confidence Sources
- deterministic confidence (high by explicit evidence),
- inferred confidence (model/policy output),
- conflict penalty adjustments,
- temporal staleness adjustments.

## Propagation Rules
- confidence must propagate to downstream continuity/link records,
- confidence decays when supporting evidence weakens over time,
- conflicting evidence creates confidence separation, not forced averaging.

## Replay Behavior
- confidence changes across versions must be attributable,
- replay reports confidence distribution drift.
