# Operator Action Model

## Action Catalog
- set scheduled polling mode (global on/off),
- trigger connector ingestion (workspace + connector scope),
- replay phase scope,
- replay object scope,
- replay connector scope,
- reprocess workspace scope,
- pause/resume connector,
- flush queue lane,
- clear ambiguity queue scope,
- invalidate extraction version scope,
- restart phase worker scope,
- quarantine corruption scope.

## Action Contract Fields
- scope,
- blast radius,
- preconditions,
- required approvals,
- rollback/recovery semantics,
- replay implications,
- audit payload requirements,
- queue lane + expected scheduling behavior.

## Ingestion-Specific Action Semantics
- `set scheduled polling mode`:
  - scope: global scheduler control.
  - effect when `OFF`: cancel future scheduled dispatch; keep manual actions available.
  - effect when `ON`: resume scheduled dispatch using existing connector runtime state.
  - safety: requires explicit confirmation because it affects all workspaces.
- `trigger connector ingestion`:
  - scope: workspace + connector (+ optional sync mode/window).
  - effect: enqueue one scoped ingestion run without changing global scheduler mode.
  - safety: must display expected queue lane and possible overlap with active runs.

## Human Digest Requirement
Before execute:
- show "what this action changes",
- "who is affected",
- "what could fail",
- "how to recover".
