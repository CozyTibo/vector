# Event Versioning Strategy

## Version Dimensions
- `schema_version`: ingestion envelope schema.
- `extraction_version`: deterministic extraction/normalization rules.
- `processor_version`: ingestion processor runtime version.
- `replay_version`: replay context policy version.
- `source_revision`: provider-native revision marker where available.

## Source Payload Evolution
- Unknown fields are preserved in payload JSONB.
- Removed source fields do not rewrite historical events.
- Parser upgrades require extraction version bump.

## Ingestion Schema Evolution
- Additive fields preferred.
- Breaking envelope changes require:
  - new schema_version,
  - migration/replay plan,
  - compatibility statement for downstream readers.
  - explicit mapping to frozen-core doctrine in `raw-envelope-contract-stability.md`.

## Immutable vs Supersedable
- Immutable:
  - source identifiers, source revision snapshot, `occurred_at`, raw payload blob.
- Supersedable metadata:
  - ingestion diagnostics, derived counters, replay comparison annotations.

## Replay-Critical Classification Link
Replay impact classification is normative in `replay-critical-fields.md`.
Fields classified as replay-critical may not change semantics without explicit breaking version transition policy.

## Backward Compatibility
- Readers must tolerate previous schema versions via version-aware parsers.
- Replay may regenerate envelopes under new version; old version artifacts retained for audit.

## Version Doctrine Link
Envelope version meaning and safe evolution policy are defined in `envelope-versioning-doctrine.md`.
