# Raw Memory Reprocessing

## Purpose
Enable extraction/canonical/linking upgrades by re-reading immutable raw evidence without mutating raw store.

## Reprocessing Workflow
1. define reprocessing scope and version targets,
2. read raw events by deterministic scope query,
3. emit reprocessing input stream with original provenance and version context,
4. write downstream superseding artifacts in later phases,
5. keep raw store unchanged.

## Safety Rules
- reprocessing cannot rewrite raw payload rows.
- reprocessing must remain replay-comparable through version metadata.
- reprocessing scans must preserve chronological semantics.

## Upgrade Support
Supports:
- extraction improvements,
- canonical mapping upgrades,
- identity linking upgrades,
- reasoning model upgrades,
while keeping raw memory substrate stable.
