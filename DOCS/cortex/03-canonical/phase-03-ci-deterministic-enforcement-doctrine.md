# Phase 03 — CI Deterministic Enforcement Doctrine

**Status:** normative operational contract.  
**Purpose:** make CI the **default enforcement layer** for drift, not human vigilance. Structural checks only—no semantic ranking.

## Scope

CI systems **MUST** enforce:

1. **Registry integrity** — hashes, signatures, lifecycle legality (`phase-03-mapping-bundle-registry.md`).
2. **Oracle replay** — manifests PASS (`phase-03-oracle-vectors-doctrine.md`).
3. **Logical-key drift** — regression sentinel across merges.
4. **Rebuild equivalence** — subset on golden scenarios.
5. **Ambiguity thresholds** — explosion sentinels (policy numeric caps per repo config).
6. **Provenance continuity** — structural absence checks for orphan edges / missing raw pointers.
7. **Deterministic ordering** — canonical sort-key validation on fixtures.
8. **Forbidden nondeterministic inputs** — lint: no wall-clock in identity paths, no random seeds in transforms.

---

## Mandatory CI gates before bundle promotion

**candidate → approved** requires artifact:

- `ci_promotion_report` with **PASS** bit + **manifest hash** + **oracle manifest hash** + **bundle manifest hash**.

Failure ⇒ promotion **blocked**.

---

## Hash verification expectations

CI **MUST** recompute artifact hashes from checked-in sources and compare to bundle records **before** merging registry updates.

---

## Fail-open vs fail-closed policy

| Surface | Policy |
| ------- | ------ |
| **Merge to registry / bundles** | **Fail-closed** on hash mismatch or oracle FAIL |
| **Application deploy containing mapping artifacts** | **Fail-closed** if promotion suite absent |
| **Replay/rebuild job dispatch** | **Fail-closed** if job pin resolves to bundle lacking oracle PASS for declared slice |
| **Operator-read dashboards** | **Fail-open** on telemetry gaps **only** if correctness gates unaffected—never for bundle promotion |

---

## Certification gate coupling

Step **18** certification requires archived:

- signed `ci_promotion_report` lineage,
- oracle manifest hashes,
- rebuild equivalence summaries,

satisfying **G-P03-12** and visibility gates **G-P03-15–G-P03-21** (`phase-03-closure-gates-doctrine.md`).

---

## Artifact retention expectations

CI artifacts **SHALL** be retained **≥** certification retention policy (minimum: match SOC-style evidence retention default chosen by org—**must be explicit** in ops policy).

---

## Signed verification report expectations

`verification_report` artifacts **SHOULD** be signed (org key). Unsigned reports **cannot** satisfy highest assurance tiers for Step **18**.

---

## Reproducibility requirements

Given identical:

- VCS commit,
- bundle manifests,
- oracle fixtures,

CI **MUST** reproduce identical report hashes (byte-stable outputs).

---

## Failure routing

| CI failure class | Blocks merge/deploy | Blocks replay job | Blocks certification | Operator review only |
| ---------------- | ------------------- | ----------------- | --------------------- | --------------------- |
| Hash mismatch | **Yes** | **Yes** | **Yes** | No |
| Oracle logical-key drift | **Yes** | **Yes** | **Yes** | No |
| Ordering drift | **Yes** | **Yes** | **Yes** | No |
| Ambiguity explosion threshold | Warn→fail per policy | Policy | Eventually **Yes** | Often **Yes** early |
| Perf regression | Optional gate | No | No | **Yes** |

---

## Divergence class enforcement

CI suites **MUST** include expectations for **C0–C5** detectors aligning with `phase-03-replay-versioning-doctrine.md` (verification engine taxonomy references **C0–C5** consistently).

---

## Forbidden nondeterministic inputs (CI lint)

Static checks **SHALL** reject merges introducing:

- undeclared randomness in mapping paths,
- wall-clock reads in logical-key derivations,
- unordered iteration affecting emitted sets without canonical sorting pass.

---

## References

- Oracle vectors: `phase-03-oracle-vectors-doctrine.md`
- Registry: `phase-03-mapping-bundle-registry.md`
- Verification engine: `phase-03-verification-engine-doctrine.md`
- Closure gates: `phase-03-closure-gates-doctrine.md`
- Readiness audit: `phase-03-implementation-readiness-audit.md`
