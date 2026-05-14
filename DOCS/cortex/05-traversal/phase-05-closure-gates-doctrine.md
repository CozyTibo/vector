# Phase 05 — Closure gates doctrine (certification pack)

**Normative step:** **26**. **Freeze bundle:** **FF-5** (terminal).  
**Depends on:** `phase-05-verification-gates-doctrine.md`, `phase-04-closure-gates-doctrine.md` (analog), `phase-05-readiness-economics-doctrine.md`.

---

## 1. Constitutional intent

Define **constitutional completion** artifacts: certification archives, closure matrix, **`G-P05-CLOSE-01`**, analog to P04 org pack — proving OCTS is **Frozen**-eligible.

---

## 2. Explicit anti-goals

- Closing phase with failing **hard_fail** gates waived silently.  
- Certification pack omitting `octs_schema_version` / `PHASE05_PROGRAM_FREEZE_VERSION`.

---

## 3. Formal terminology

| Artifact | Role |
| -------- | ---- |
| **OCTS certification pack** | Bytes per **`OCTS-CERT-PACK-1`** (`phase-05-certification-pack-format.md`); verified by **`G-P05-CLOSE-01`**. |
| **Closure matrix** | Table: gate id × environment × pass/fail + commit sha. |
| **G-P05-CLOSE-01** | Aggregate check: all `hard_fail` gates green + pack_hash match + FF-5 checklist complete. |

---

## 4. Deterministic semantics

Pack canonicalization **MUST** include sorted keys, include `engine_build_id`, `derivation_rule_versions[]`, `gate_results` sorted by gate id.

---

## 5. Replay semantics

Recomputing `pack_hash` from archived inputs **MUST** match stored hash or closure **FAILS**.

---

## 6. Temporal semantics

Pack records `anchor_used_for_certification` — pinned instant for snapshot claims.

---

## 7. Provenance semantics

Pack references `verification_run_id`, `tenant_id` (fixture or production cert tenant).

---

## 8. Serialization contracts

Binary / on-disk layout, manifest, gzip+tar ordering, and hash slots — **`phase-05-certification-pack-format.md`** (**only**). Runtime module **`vector.domains.cortex.traversal.certification_pack`** **MUST** implement that format byte-for-byte.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-CG-01** | Closure with `OCTS_VERIFICATION_MODE!=strict` on CI lane. |
| **FS-CG-02** | Pack includes exploration walks as authoritative evidence. |

---

## 10. Verification implications

**G-P05-CLOSE-01** runs **after** core **G-P05-*** suite in runner ordering to avoid recursion (mirror P04 pattern).

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Release mgr | Waive gate without ticket | Waiver file requires ticket UUID + expiry. |

---

## 12. Negative examples

**ILLEGAL:** closure matrix row `G-P05-IMPORT-01` = `skipped`.

---

## 13. CI oracle expectations

Golden certification pack in fixtures; tamper one byte → hash mismatch test.
