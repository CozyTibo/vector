# Temporal Identity Model

## Objective
Represent identity continuity and drift across time.

## Temporal Elements
- identity validity windows (`effective_from`, `effective_to`),
- merge/split timestamps,
- supersession links,
- chronology anchors from canonical/ raw evidence.

## Temporal Rules
- identity changes are represented as new versioned continuity records,
- historical states remain queryable,
- no latest-state overwrite without lineage.
