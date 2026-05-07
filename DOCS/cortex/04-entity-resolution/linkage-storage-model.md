# Linkage Storage Model

## Storage Objects
- linkage records table,
- continuity records table,
- ambiguity records table,
- linkage conflict records,
- linkage replay divergence metadata.

## Persistence Boundaries
- writes only linkage-layer outputs and control metadata,
- no mutation of canonical/raw truth objects,
- supersession used for state evolution.

## Persistence Requirements
- provenance + temporal + confidence + version fields mandatory,
- replay metadata attached for replay-produced outputs.
