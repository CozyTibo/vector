# Phase 05 — Hop receipt doctrine

**Normative step:** **10**. **Freeze bundle:** **FF-3**.  
**Depends on:** `phase-05-multigraph-model-doctrine.md`, `phase-05-observed-vs-derived-doctrine.md`, `phase-05-walk-result-contract.md`.

---

## 1. Constitutional intent

Bind each hop to **machine-checkable evidence**: org link id, **edge_fingerprint**, validity snapshot, optional primitive evidence — enabling **dangling evidence** detection and dedup semantics.

---

## 2. Explicit anti-goals

- Receipts without `hop_sequence`.  
- Duplicate “same hop” collapsed when `hop_sequence` differs (multi-visit allowed only if policy explicitly **`allow_revisit_vertices`** — then receipts **MUST** remain distinct).

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **Evidence envelope** | `{ org_link_id, edge_fingerprint, validity_half_open, source_node_id, target_node_id }` minimum for observed. |
| **Dangling evidence** | `org_link_id` not found in pinned projection — **ILLEGAL** for observed hops. |

---

## 4. Deterministic semantics

**RULE HR-01:** `hop_sequence` is **0..N-1** contiguous.  
**RULE HR-02:** **Receipt dedup:** Two hops with identical `edge_fingerprint` and same `hop_sequence` **ILLEGAL**; identical fingerprint at different sequences **ALLOWED** only if `allow_revisit_vertices=true`.

---

## 5. Replay semantics

Replay **MUST** reproduce identical receipt list for observed-only walks.

---

## 6. Temporal semantics

`validity_half_open` on receipt **MUST** equal export at anchor; mismatch → `invalid_edge_at_t` diagnostic.

---

## 7. Provenance semantics

Derived hops **MUST** include `derivation_rule_id` and **MUST** omit `org_link_id` **only if** primitive-only edge — see graph import (rare); default **requires** `org_link_id`.

---

## 8. Serialization contracts

Canonical hop receipt keys sorted; `evidence_envelope` nested object sorted.  
**Dangling handling:** if policy `allow_dangling_evidence_refs=false` (default), missing link → **fail walk** with `dangling_evidence` error code.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-HR-01** | Observed hop missing `edge_fingerprint`. |
| **FS-HR-02** | Fingerprint does not match recomputed law from envelope fields. |
| **FS-HR-03** | `provenance_class=derived` with `org_link_id` present but `derivation_rule_id` absent. |

---

## 10. Verification implications

- **G-P05-HR-01:** Fingerprint recomputation from envelope.  
- **G-P05-HR-02:** Dangling reference injection tests.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Downstream | Treat receipt as causal “because link existed” | Receipt is structural; causal claims require Phase 06 artifacts. |

---

## 12. Negative examples

**ILLEGAL:**

```json
{ "hop_sequence": 0, "provenance_class": "derived", "authority_binding": { "org_link_id": "x" } }
```

(missing `derivation_rule_id`)

---

## 13. CI oracle expectations

Property: ∀ hops, fingerprint recomputes; revisit policy matrix fully covered.

---

## 14. Reference implementation (runtime)

- **Module:** `vector.domains.cortex.traversal.hop_receipt_contract` (re-exported from `vector.domains.cortex.traversal`).
- **Static gates:** **G-P05-HR-01** (`verify_gp05_hr01_fingerprint_recompute_from_envelope_static`), **G-P05-HR-02** (`verify_gp05_hr02_dangling_org_link_rejected_static`).
- **Walk result integration:** `validate_walk_result_hash_body_contract_v1` calls `validate_hop_receipt_list_for_hash_body_v1` when `hop_receipts` is non-empty (dangling enforcement requires caller-supplied pinned links + policy; hash-body-only validation skips dangling). Optional ``skip_reason`` on each receipt is validated when present (**P05-12** / **FS-WD-01**).
- **Fixtures:** `backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/hop_receipts/`.
- **Pytest:** `backend/tests/vector/domains/cortex/traversal/test_phase05_step10_hop_receipt_contract.py`.
