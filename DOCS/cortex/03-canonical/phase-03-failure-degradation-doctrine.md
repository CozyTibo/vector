# Phase 03 — Failure & Degradation Doctrine

**Status:** normative.

## Principle

Canonicalization failures must **not** silently corrupt truth. Prefer **no canonical assertion** plus explicit degraded state over wrong assertions.

## Failure / state taxonomy

| State | Meaning | Operator-visible |
| ----- | ------- | ------------------ |
| **Healthy** | Canonical projections succeeded per gates | Yes |
| **Degraded** | Partial scope processed; explicit reasons | Yes |
| **Partial** | Some projections skipped due to missing mapping/evidence | Yes |
| **Unresolved** | Ambiguity records emitted | Yes |
| **Unverifiable** | Cannot attach provenance to assert a row | Must block emission or emit marked non-authoritative stub per gates |
| **Conflicting** | Contested structured facts preserved | Yes |
| **Corrupted** | Internal invariant violated (duplicate keys, missing lineage) | FAIL — halt scope |

## Canonicalization-specific failures

- **Mapping gap:** emit unresolved mapping ambiguity; do not guess.
- **Trust substrate RED:** canonicalization must consult Phase 02 trust signals; if doctrine demands halt on catastrophic trust states, obey (exact wiring in implementation plan).

## Replay degradation

If rebuild cannot match stored rows:

- Surface divergence classes (`phase-03-replay-versioning-doctrine.md`),
- Never auto-delete conflicting canonical rows without explicit regulated tombstone workflow.

## References

- Remediation actions (runtime): `phase-03-remediation-recovery-doctrine.md`
- Operator visibility: `phase-03-canonical-control-plane-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
