# Phase 02 Reconstruction Semantics Doctrine

## Core Rule
Historical reconstruction in Phase 02 means:
"reconstruct preserved observed evidence for scope/time."

It does not mean:
"reconstruct objective omniscient provider reality."

## Supported Reconstruction Modes
- as_of_T: evidence observed and valid at timestamp T.
- latest_before_T: latest preserved revision at or before T.
- window_slice: evidence preserved within [T1, T2].
- replay_safe_slice: evidence slice satisfying replay-safe constraints.

## Guarantee Boundary
Phase 02 guarantees reconstruction of preserved rows and preserved lineage.
Phase 02 does not guarantee:
- states never observed,
- upstream deletions before first capture,
- complete restoration of provider-retroactive mutations.

## Gap Semantics
Every reconstruction response must be classifiable:
- reconstruction-safe,
- partial reconstruction,
- reconstruction-limited,
- unverifiable reconstruction.

Gap classes to expose:
- missing evidence window,
- lineage gap,
- revision gap,
- corruption-affected range,
- replay-diverged range.

## Examples
- Slack message deleted before ingestion: unavailable; reported as missing-history, not silent omission.
- GitHub object mutated upstream later: preserved older observed revision remains reconstructable; later divergence is surfaced.
- Replay after provider deletion: replay uses preserved evidence; absent upstream data is reported as non-observed.
