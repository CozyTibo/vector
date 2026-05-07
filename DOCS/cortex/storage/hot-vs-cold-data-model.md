# Hot vs Cold Data Model

## Objective
Define temperature-aware data placement while preserving replay and lineage reconstructability.

## Temperature Tiers
- Hot: active ingestion/canonical/linkage states and active incidents.
- Warm: recent historical windows with moderate operational query frequency.
- Cold: long-horizon history, superseded states, older transcript payloads.

## Replay Requirement
Cold data remains replay-accessible via deterministic retrieval/rehydration flows.

## Tiering Principles
- keep frequently filtered metadata in hot/warm tiers,
- move heavy payload bodies cold when operationally safe,
- preserve indexable lineage anchors even when payloads cool.

## Risks
- cold tier access latency can destabilize replay windows,
- over-aggressive cooling can break operator debugging ergonomics,
- uneven data movement policies can create reconstruction gaps.

## Guardrail
Data temperature policy cannot break trust-critical queries: replay, provenance chain validation, incident timeline reconstruction.
