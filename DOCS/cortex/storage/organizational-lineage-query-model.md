# Organizational Lineage Query Model

## Objective
Enable reconstruction of organizational causality (decisions, execution, ownership, artifacts) across time and tools.

## Lineage Domains
- execution lineage (intent -> work -> outcome),
- discussion lineage (thread evolution and decision influence),
- initiative lineage (scope/ownership/priority shifts),
- artifact lineage (doc/spec/code/ticket relationships),
- decision lineage (evidence, alternatives, supersession).

## Query Modes
- backward attribution: "why did this happen?",
- forward impact: "what did this affect?",
- continuity neighborhood: "what context surrounds this anchor?".

## Graph-Like Pressure
- variable-depth traversal with branching,
- temporal validity filtering on edges,
- ambiguity branches that must remain inspectable.

## Relational Risk
Without targeted acceleration, recursive lineage queries can become too slow for incident/debugging windows.

## Practical Strategy
Keep relational source-of-truth; add lineage-oriented read accelerators only when measured traversal latency exceeds operational thresholds.
