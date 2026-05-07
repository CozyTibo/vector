# Failure Explanation Model

## Objective
Convert low-level operational failures into actionable human explanations.

## Required Explanation Fields
- what failed (component + phase),
- why it failed (failure class + root-cause hypothesis),
- where it failed (scope and lineage step),
- downstream effects,
- replay implications,
- recovery options ranked by safety.

## Explanation Quality Rules
- no opaque error-only output.
- include confidence on root-cause when uncertain.
- include evidence links to logs/runs/checkpoints/provenance chain.
