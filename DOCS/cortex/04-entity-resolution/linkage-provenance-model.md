# Linkage Provenance Model

## Objective
Ensure every identity/linkage outcome is traceable to canonical and raw evidence.

## Provenance Requirements
- lineage chain id for every linkage record,
- input canonical refs,
- source raw refs reachable through canonical lineage,
- transformation stage and version tuple,
- replay context when applicable.

## Continuity Rules
- no linkage persisted without provenance,
- provenance discontinuity sets linkage trust to untrusted.
