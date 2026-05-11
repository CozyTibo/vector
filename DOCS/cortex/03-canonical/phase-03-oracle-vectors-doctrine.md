# Phase 03 — Oracle Vectors & Deterministic Regression Doctrine

**Status:** normative.  
**Purpose:** elevate oracle vectors from “tests” to **existential replay-safety infrastructure**: the canonical analogue of crypto oracle proofs for structural transforms.

Everything herein remains **structural, deterministic, provenance-safe**—no semantic interpretation.

## Definitions

| Term | Definition |
| ---- | ---------- |
| **Oracle vector** | Frozen tuple: `(fixture_id, raw_snapshot_ref, mapping_bundle_id, engine_build_ref, expected_outputs)` where expected outputs include logical keys, ordering keys, ambiguity records, provenance edges — **machine-diffable**. |
| **Oracle manifest** | Ordered inventory of oracle vectors + coverage tags + bundle/engine bindings for a promotion boundary. |
| **Golden reconstruction scenario** | End-to-end oracle spanning raw fixtures → canonical projection → rebuild equivalence assertion within allowed C-class. |

---

## Canonical oracle vector structure (required fields)

Each oracle vector **SHALL** declare at minimum:

1. **fixture_id** — stable string ID.
2. **coverage_tags** — from mandatory categories (below).
3. **raw_snapshot_ref** — content-addressed Phase 02 raw fixture corpus slice.
4. **mapping_bundle_id** + **manifest hash** pinned.
5. **engine_build_ref** — deterministic engine identifier (git SHA / build stamp schema TBD by implementation—must be **explicitly comparable**).
6. **expected_logical_keys** — per-class tuples per `phase-03-logical-key-doctrine.md`.
7. **expected_ordering** — per temporal doctrine sort keys.
8. **expected_ambiguity_records** — explicit sets (may be empty).
9. **expected_provenance_edges** — minimal forward index slice for traceability gates.
10. **allowed_divergence_classes** — normally **{C0}** for pure replay; migration suites may declare **C2** with receipts.

---

## Mandatory coverage categories

Oracle suites **SHALL** include vectors spanning at minimum:

- **Per canonical class** logical-key stability,
- **Temporal ordering**—late arrival + supersession,
- **Ambiguity persistence**—competing rules / unresolved mapping,
- **Provenance continuity**—multi-source edges,
- **Rebuild equivalence**—recompute matches stored within allowed C-class,
- **Drift-class detectors**—fixtures prove **C3/C4/C5** classification paths trigger when injected (adversarial fixtures).

---

## Deterministic replay assertions

Oracle execution **MUST** assert:

1. **Bitwise or declared-normalization equivalence** of canonical outputs vs expected (`phase-03-replay-versioning-doctrine.md`).
2. **Ordering equality** under canonical sort discipline.
3. **No duplicate logical keys** for authoritative tuples.
4. **Ambiguity records** match exactly—silent drops **FAIL**.

---

## Mandatory oracle execution before promotion

**candidate → approved** **blocked** unless:

- Full oracle manifest for the bundle’s **declared coverage slice** **PASS**,
- Compatibility-line oracle subset **PASS** for each declared non-breaking edge (`phase-03-mapping-bundle-registry.md`).

---

## Oracle failure severity

| Failure kind | Classification | Effect |
| ------------ | -------------- | ------ |
| Logical-key mismatch vs expected | **Hard-blocking** | Blocks promotion; opens remediation |
| Ordering mismatch | **Hard-blocking** | Blocks promotion |
| Missing provenance edge | **Hard-blocking** for traceability gates | Blocks promotion |
| Ambiguity count mismatch | **Hard-blocking** when doctrine demands persistence | Blocks promotion |
| Rebuild equivalence outside allowed C-class | **Hard-blocking** | Blocks promotion & certification |
| Performance-only regression | **Non-blocking for correctness** | Operator review / perf gate |

---

## Compatibility-line regression expectations

For each declared **non-breaking** edge **A→B**, oracle suite **SHALL** include:

- fixtures proving remap produces **C2-or-better** with explicit receipt shape,
- absence of undeclared key drift (**else C5**).

---

## Adversarial fixture requirements

Minimum adversarial vectors:

1. **Raw-trust mismatch injection** → expect **C3** path (`phase-03-replay-versioning-doctrine.md`).
2. **Engine nondeterminism simulation** (e.g., unordered iteration if introduced) → expect **C4**.
3. **Compatibility gap** (bundle jump without line) → expect **C5**.

---

## Certification invalidation

Oracle failures on **certification pinned bundles** **invalidate Step 18 certification** for affected slices until vectors pass and evidence pack refreshed.

---

## Ownership

- **Bundle owners** maintain oracle manifests alongside bundles.
- **Verification engineering** owns harness runner contracts (`phase-03-verification-engine-doctrine.md`).
- **CI system** enforces execution frequency & promotion coupling (`phase-03-ci-deterministic-enforcement-doctrine.md`).

---

## References

- Logical keys: `phase-03-logical-key-doctrine.md`
- Replay / C-classes: `phase-03-replay-versioning-doctrine.md`
- Registry: `phase-03-mapping-bundle-registry.md`
- CI enforcement: `phase-03-ci-deterministic-enforcement-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
