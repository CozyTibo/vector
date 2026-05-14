# Phase 05 — Specification gap matrix (OCTS)

**Status:** normative — **P0/P1 cleared for doctrine v1 closure** (2026 constitutional closure pass).  
**Role:** track **P2** refinements, **amendments**, and **operational** follow-ups only. **Active P0** section **MUST** remain empty unless a regression reopens a constitutional hole.

---

## Active P0

*(none — frozen for specification purposes.)*

---

## Active P1

*(none — any reopened semantic hole **MUST** be filed here with owner + freeze impact before merge.)*

---

## Resolved P0 (reference — do not delete)

| ID | Was | Resolution document / section |
| -- | --- | ------------------------------ |
| **GAP-P0-01** | Snapshot / export total order | `phase-05-temporal-walk-doctrine.md` §3–§3.4 (`export_sequence`, concurrent export rules) |
| **GAP-P0-02** | Idempotency canonicalization | `phase-05-canonicalization-profile.md` §7 + `phase-05-idempotency-and-retry-doctrine.md` §8 |
| **GAP-P0-03** | Fixture home | `phase-05-ci-enforcement-architecture.md` §7 + `backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/README.md` |
| **GAP-P0-04** | Certification pack | `phase-05-certification-pack-format.md` (**OCTS-CERT-PACK-1**) |
| **GAP-P0-05** | `engine_build_id` | `phase-05-traversal-equivalence-doctrine.md` §3 |

---

## P2 (non-blocking refinements)

| ID | Topic | Owner |
| -- | ----- | ----- |
| **GAP-P2-01** | Schemathesis optional fuzzing for walk API | API contracts |
| **GAP-P2-02** | Operator UI copy deck for diagnostics enums | Control plane (non-normative) |

---

## Strength legend

| Label | Doctrine | Enforcement |
| ----- | -------- | ----------- |
| **Frozen** | No **P0**/**P1** affecting slice; text locked unless amendment | N/A (this matrix tracks doctrine only here) |
| **Strong** | Same as pre-pass **Strong** | See `phase-05-ci-enforcement-architecture.md` |

**Doctrine v1 closure:** Phase 05 normative text for Steps **1–26** is treated as **Frozen** at the specification layer **subject to** `waivers/verification_waivers.yaml` and future amendments. **Runtime** and **CI execution** remain **not Frozen** until code ships — see `phase-05-runtime-legality-matrix.md`.

---

## Per-step doctrine strength (post-closure)

| Step | Doctrine file | Doctrine | Notes |
| ---- | ------------- | -------- | ----- |
| 1–26 | *(per `phase-05-normative-index.md`)* | **Frozen** | Cross-links to **OCTS-CANON-1**, **CI-ARCH**, **CERT-PACK-1** where applicable |
| shared | `phase-05-idempotency-and-retry-doctrine.md` | **Frozen** | |

---

## Amendments

Amendments **MUST** append a row:

| Date | ID | Change | Approver |
| ---- | -- | ------ | -------- |

---

## Review cadence

Any PR that weakens an invariant **MUST** update this file **before** merge.
