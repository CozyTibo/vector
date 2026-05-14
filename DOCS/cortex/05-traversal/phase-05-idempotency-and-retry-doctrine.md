# Phase 05 — Idempotency and retry doctrine

**Normative step:** **shared (14–21, 17–18)**. **Freeze bundle:** **FF-4** (design), **FF-5** (full).  
**Depends on:** `phase-05-normative-index.md`, `phase-05-index-build-job-doctrine.md`, `phase-05-walk-replay-doctrine.md`.

---

## 1. Constitutional intent

Guarantee **safe retries** and **exactly-once semantics** for **observable side effects** (epoch bumps, publishes, walk archival) while allowing **at-least-once** task delivery.

---

## 2. Explicit anti-goals

- Double-publish same `index_epoch` with different hashes.  
- “Retry” that mutates `walk_id` for same client idempotency key.  
- Cache contamination: serving cached walk result for different `policy_hash`.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **Client idempotency key** | Header `Idempotency-Key` on POST walk — UUID recommended. |
| **Server idempotency record** | Stores `(key_hash → walk_id, walk_result_hash, created_at)` TTL. |
| **Job idempotency key** | Derived per index replay doctrine / index build. |

---

## 4. Deterministic semantics

**RULE IR-01:** Same `Idempotency-Key` + same **`body_identity_hash`** per **`OCTS-CANON-1` §7** ⇒ **same** `walk_result_hash` or **`409`** with pointer to original `walk_id`.  
**RULE IR-02:** Same key + different `body_identity_hash` ⇒ **`409`** `idempotency_key_conflict`.

---

## 5. Replay semantics

Replay jobs use **job idempotency key**; reruns **MUST** detect `COMMITTED` receipt and exit 0 without mutation.

---

## 6. Temporal semantics

Idempotency records **MUST** include `SHA256(octs_canonical_json(temporal_anchor))` in key material when anchor is part of request.

---

## 7. Provenance semantics

Duplicate detection **MUST NOT** drop receipt history — returns prior artifact reference.

---

## 8. Serialization contracts

**GAP-P0-02 — CLOSED.** Single law: **`phase-05-canonicalization-profile.md` §7** (`body_identity_bytes` + `body_identity_hash`). **MUST NOT** use raw-byte compare.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-IR-01** | Two successful publishes same epoch. |
| **FS-IR-02** | Retry generates different receipts for identical logical walk. |
| **FS-IR-03** | Shared in-memory cache across tenants without key prefix. |

---

## 10. Verification implications

- **G-P05-IDEM-01:** HTTP replay matrix tests.  
- **G-P05-IDEM-02:** Celery duplicate delivery simulation.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Client | Replay attack swaps body | **`body_identity_hash`** per **`OCTS-CANON-1`** detects logical change |

---

## 12. Negative examples

**ILLEGAL:** return 200 with new `walk_id` for same idempotency key.

---

## 13. CI oracle expectations

Concurrency tests with N workers hammering same key; Redis/DB lease semantics **MUST** match `phase-05-index-build-job-doctrine.md` (no undefined behavior).
