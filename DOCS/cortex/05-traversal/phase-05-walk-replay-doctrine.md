# Phase 05 — Walk replay doctrine

**Normative step:** **19**. **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-walk-result-contract.md`, `phase-05-temporal-walk-doctrine.md`, `phase-05-idempotency-and-retry-doctrine.md`, `phase-05-traversal-equivalence-doctrine.md`.

---

## 1. Constitutional intent

Define **walk regeneration** from pinned inputs so walk artifacts are **replay-safe evidence** comparable in CI and certification.

---

## 2. Explicit anti-goals

- Replay that silently upgrades exploration to authoritative.  
- Replay without `policy_hash` pin.  
- Accepting “close enough” hashes.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **Walk replay job** | Celery/async job with inputs: `walk_id` **or** full pinned request snapshot. |
| **Replay receipt** | Artifact proving `(input_hash, output_walk_result_hash, engine_build_id)` |

---

## 4. Deterministic semantics

**RULE WRJ-01:** Replay comparator **MUST** canonicalize both sides with same `octs_schema_version` or declare **incompatible** error.  
**RULE WRJ-02:** **Async permutation legality:** If async scheduling reorders unrelated jobs, **walk replay equivalence** **MUST** still hold per equivalence doctrine — walk itself single-threaded.

---

## 5. Replay semantics

**REPLAY REQUIREMENT WRJ-01:** `output_walk_result_hash == expected_hash` or job **FAILS**.  
**REPLAY REQUIREMENT WRJ-02:** Inputs **MUST** include: **`temporal_anchor`** (full object per `phase-05-temporal-walk-doctrine.md` §3.1), **`policy_hash`**, **`start_node_ids`**, **`walk_execution_strategy`**, **`exploration_mode`**, **`pinned_index_epoch`** (nullable only when strategy is pure `ONLINE_OBSERVED`), **`octs_schema_version`**, **`engine_build_id`** (telemetry field, not in walk hash).

**REPLAY REQUIREMENT WRJ-03 — Cancellation:** On replay of a **cancelled** walk, `hash_body` **MUST** match the original completed `hash_body` per `phase-05-runtime-legality-matrix.md` §7 (partial tail outside hash).

**REPLAY REQUIREMENT WRJ-04 — Stale derived index:** If original walk pinned `pinned_index_epoch` and that epoch row is **missing**, replay **MUST** **`fail`** authoritative replay with `index_epoch_unavailable`. If policy had `allow_stale_derived_read=true`, replay **MUST** reproduce the same **non-authoritative** flags and `walk_result_hash` as original (fixture proves).

**REPLAY REQUIREMENT WRJ-05 — Missing derived store:** Same as WRJ-04 — **no** silent online fallback.

**REPLAY REQUIREMENT WRJ-06 — Supersession:** If `export_sequence` in anchor is **older** than latest committed export for tenant, replay **MUST** still load **exact** bytes stored for that sequence; if bytes were **garbage-collected**, **`410`** `export_evicted` (not `dangling_evidence`).

---

## 6. Temporal semantics

If export no longer contains an edge referenced in historical walk:

| Mode | Behavior |
| ---- | -------- |
| **authoritative** (default) | **`fail`** `dangling_evidence` |
| **`best_effort_exploration`** | **Only** when `exploration_mode=true` in replay input; **MUST** set `non_authoritative=true`; **MUST** use `termination_reason` ∈ {`policy_rejected`, `empty_frontier`, `budget_exhausted`} — **FORBIDDEN** to emit `dangling_evidence` in this mode |

**INVARIANT WRJ-TAX:** `dangling_evidence` **MUST** appear **only** for authoritative replay failures.

---

## 7. Provenance semantics

Replay receipt **MUST** link prior `walk_id` and `original_walk_result_hash`.

---

## 8. Serialization contracts

Job payload **MUST** be `octs_canonical_json(...)` per **`OCTS-CANON-1`**.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-WRJ-01** | Replay overwrites live `walk_id` result row. |
| **FS-WRJ-02** | Mismatch ignored in strict mode. |

---

## 10. Verification implications

- **G-P05-REPLAY-WALK-01:** Nightly replay of sampled walks.  
- **G-P05-REPLAY-WALK-02:** Mutation of single edge changes hash predictably.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Compliance | “Replay passed” with relaxed compare | Strict mode is CI default for org certification pack. |

---

## 12. Negative examples

**ILLEGAL:** `expected_hash` omitted from replay job in strict mode.

---

## 13. CI oracle expectations

Archive golden walks in tenant certification fixtures; replay job runs in <5s for CI slice.
