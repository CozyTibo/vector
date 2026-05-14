# Phase 05 — Index replay doctrine

**Normative step:** **20**. **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-derived-index-contract-doctrine.md`, `phase-05-index-build-job-doctrine.md`, `phase-05-idempotency-and-retry-doctrine.md`.

---

## 1. Constitutional intent

Define **index regeneration** and **hash equality** laws so derived structures never drift silently from authoritative inputs.

---

## 2. Explicit anti-goals

- Accepting index rebuild that “mostly matches.”  
- Skipping lineage validation for performance.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **index_content_hash** | SHA-256 over canonical derived artifact per derived index contract. |
| **Regeneration job** | Rebuild from shadow + validate + optional publish. |

---

## 4. Deterministic semantics

**RULE IRJ-01:** Given same `projection_content_hash` + `derivation_rule_id` + `target_schema_version`, rebuild **MUST** yield identical `index_content_hash`.  
**RULE IRJ-02:** **index_epoch** increments **only** on successful `COMMITTED` publish after validation.

---

## 5. Replay semantics

Double-run regeneration on cold replica **MUST** match hash — **G-P05-REPLAY-IDX-01**.

---

## 6. Temporal semantics

Rebuild **MUST** use same `materialized_for_anchor` as recorded in job unless explicitly rebuilding “latest” with new anchor (creates **new** job lineage).

---

## 7. Provenance semantics

Publish receipt lists all `source_observed_edge_fingerprints` cardinality stats — telemetry.

---

## 8. Serialization contracts

Canonical derived artifact format version `DERIVED_INDEX_CANON_VERSION` in hash preamble.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-IRJ-01** | Publish without lineage scan pass. |
| **FS-IRJ-02** | Hash match with missing nodes vs reference (incomplete compare). |

---

## 10. Verification implications

- **G-P05-REPLAY-IDX-01:** Double-run hash equality.  
- **G-P05-REPLAY-IDX-02:** Corrupt single lineage edge → deterministic failure.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Storage | Bitrot in adjacency | Hash + spot lineage checks. |

---

## 12. Negative examples

**ILLEGAL:** `COMMITTED` when lineage scan reported WARN without waiver id.

---

## 13. CI oracle expectations

Large synthetic graph rebuild under memory cap; compare hashes across OS.
