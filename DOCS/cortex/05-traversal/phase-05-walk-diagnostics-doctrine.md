# Phase 05 — Walk diagnostics doctrine

**Normative step:** **12**. **Freeze bundle:** **FF-3**.  
**Depends on:** `phase-05-walk-result-contract.md`, `phase-05-walk-policy-doctrine.md`.

---

## 1. Constitutional intent

Provide a **closed taxonomy** of machine-readable termination and skip reasons — enabling operator control plane and CI without natural language.

---

## 2. Explicit anti-goals

- Free-text diagnostics in canonical body.  
- Vendor-specific error strings in hashed fields.

---

## 3. Formal terminology

| Term | Meaning |
| ---- | ------- |
| **termination_reason** | Closed enum on walk result. |
| **skip_reason** | Per-hop enum when hop skipped by policy. |

**Normative enum `termination_reason` (v1):**  
`target_reached` | `budget_exhausted` | `empty_frontier` | `cycle_cut` | `invalid_edge_at_t` | `policy_rejected` | `error_internal` | `dangling_evidence` | `import_hash_mismatch`

**Normative enum `skip_reason` (v1):**  
`not_in_allowlist` | `filtered_by_authority` | `invalid_at_t` | `deduped_revisit_forbidden`

---

## 4. Deterministic semantics

**RULE WD-01:** On `budget_exhausted`, engine **MUST** emit last fully validated frontier state in non-hashed **telemetry** only; hash body **MUST** include `termination_reason` only.  
**RULE WD-02:** **Truncation semantics:** partial hop list **FORBIDDEN** in authoritative mode — walk either completes legally or fails with `error_internal` / `policy_rejected`.

---

## 5. Replay semantics

Diagnostics enums **MUST** match exactly across replay; any change → different hash (expected for error paths).

---

## 6. Temporal semantics

`invalid_edge_at_t` **MUST** include `offending_edge_fingerprint` in **telemetry**, optional in hash body only if also in closed struct `invalid_edge_record` (sorted keys) — if included in hash, **MUST** be stable.

---

## 7. Provenance semantics

`cycle_cut` **MUST** record `cycle_fingerprint` = SHA-256 of sorted multiset of `edge_fingerprint` on cycle (see multigraph doctrine for multiset).

---

## 8. Serialization contracts

Diagnostics objects: keys sorted; only enums + integers + fingerprints allowed — no raw URLs.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-WD-01** | Unknown enum string. |
| **FS-WD-02** | `termination_reason` missing. |
| **FS-WD-03** | Truncated receipts with `termination_reason=target_reached`. |

---

## 10. Verification implications

- **G-P05-DIAG-01:** Enum exhaustiveness test vs OpenAPI.  
- **G-P05-DIAG-02:** Cycle detection golden vectors.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Ops | Rely on English messages | Control plane maps enums to copy — not stored in OCTS hash. |

---

## 12. Negative examples

**ILLEGAL:** `"termination_reason": "stopped because slow"`  
**LEGAL:** `"termination_reason": "budget_exhausted"`

---

## 13. CI oracle expectations

Every enum value has fixture walk; unknown enum rejected at API.
