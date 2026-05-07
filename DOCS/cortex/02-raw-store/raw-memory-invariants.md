# Raw Memory Invariants

## Invariant 1: Raw Payload Immutability
- meaning: payload blob is append-only.
- replay implications: baseline replay trust.
- downstream dependencies: canonical/reasoning provenance.
- corruption symptoms: payload hash drift.
- verification expectation: immutable-row mutation checks.

## Invariant 2: Provenance Reconstructability
- meaning: raw record has sufficient provenance bootstrap fields.
- replay implications: replay equivalence proof possible.
- downstream dependencies: evidence chains.
- corruption symptoms: missing provenance refs.
- verification expectation: non-null provenance integrity scans.

## Invariant 3: Source Identity Preservation
- meaning: source ids/revisions preserved as observed.
- replay implications: deterministic dedupe and replay windowing.
- downstream dependencies: change lineage and correction handling.
- corruption symptoms: identity collisions or missing revisions.
- verification expectation: identity uniqueness + conflict probes.

## Invariant 4: Replay Lineage Durability
- meaning: replay metadata persists and remains queryable.
- replay implications: trusted reprocessing history.
- downstream dependencies: divergence diagnosis.
- corruption symptoms: orphan replay records.
- verification expectation: replay coverage and linkage audits.

## Invariant 5: Deterministic Raw Retrieval
- meaning: same query scope returns stable evidence set under fixed snapshot.
- replay implications: deterministic reconstruction.
- downstream dependencies: reproducible canonicalization reruns.
- corruption symptoms: unstable scan coverage.
- verification expectation: repeatability checks on replay scans.
