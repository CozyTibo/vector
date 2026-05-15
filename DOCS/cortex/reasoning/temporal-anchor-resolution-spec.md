# Temporal anchor resolution spec (Phase 06)

**Status:** normative spec.

## Resolution stages

1. **Ingest** anchors from raw + Phase **03/04** materializations.  
2. **Normalize** timezone + string format per connector policy table.  
3. **Order** using `temporal_anchor_resolution_order_v1`: `(export_sequence, snapshot_unix_ns, observed_at_iso, raw_record_id)`.  
4. **Declare** `replay_safe_ordering` outcome.  
5. **Emit** resolution receipt (see proof artifacts doc).

## Conflicts

Delegate to `temporal-conflict-resolution-law.md`; never pick “median time.”
