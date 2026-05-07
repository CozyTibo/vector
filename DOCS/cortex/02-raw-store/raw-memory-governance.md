# Raw Memory Governance

## Governance Scope
Controls change management for raw memory semantics, replay trust, provenance continuity, and retention policy evolution.

## Changes Requiring Replay Review
- replay scope semantics,
- replay version pinning model,
- replay retrieval ordering rules.

## Changes Requiring Provenance Review
- provenance bootstrap field changes,
- source identity preservation changes,
- archival lineage mapping changes.

## Changes Requiring Storage Review
- index model changes on replay-critical paths,
- partitioning model changes,
- archival pointer/storage substrate changes.

## Changes Requiring Retention Review
- retention horizon changes,
- deletion semantics changes,
- archival transition policy changes.

## Changes Requiring Corruption/Recovery Review
- integrity hash strategy changes,
- corruption detection threshold changes,
- recovery workflow changes.

## Governance Rule
No raw-store semantic change is approved without documented impact on replayability, provenance continuity, and historical reconstruction guarantees.
