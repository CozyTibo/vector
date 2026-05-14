# Phase 05 — Replay integrity matrix (OCTS)

**Status:** normative cross-artifact law table.  
**Pairs with:** `phase-05-walk-replay-doctrine.md`, `phase-05-index-replay-doctrine.md`, `phase-05-traversal-equivalence-doctrine.md`, `phase-05-spec-gap-matrix.md`.

---

## 1. Replay guarantees (what MUST reproduce)

| Artifact | Input pin | Output stable id | Invariant |
| -------- | --------- | ---------------- | ---------- |
| Walk result | `temporal_anchor` + `policy_hash` + starts + strategy + exploration flag | `walk_result_hash` | L-EQ-01 |
| Hop receipts | Same + neighbor law | receipt list byte-stable | OVD-01 |
| Derived index | `projection_content_hash` + `derivation_rule_id` + `DERIVED_INDEX_CANON_VERSION` | `index_content_hash` | IRJ-01 |
| Index publish | Successful validate | `index_epoch` monotonic | DI-02 |
| Economics receipt | Fixture tenant + anchor | `economics_receipt_hash` | `phase-05-readiness-economics-doctrine.md` (receipt law) |

---

## 2. Replay scope (what is in / out of scope)

| In scope | Out of scope (v1) |
| -------- | ------------------ |
| Single-tenant deterministic engine per walk | Multi-tenant parallel walks sharing one process without isolation keys |
| Celery at-least-once with idempotent side effects | Exactly-once delivery globally |
| Pinned export bytes for a fixed `(tenant_id, export_sequence)` | Live “chase tail” of changing export during walk |
| Strict hash compare | Fuzzy “semantically same path” |
| Cooperative cancel with `hash_body` law | Partial hops inside `hash_body` (**FORBIDDEN** — see `phase-05-runtime-legality-matrix.md` §7) |

**Unsupported / forbidden deployments** — see `phase-05-runtime-legality-matrix.md` §4–§5 (multi-primary, cross-region primaries, etc.).

---

## 3. Equivalence laws (summary)

| Law | Text |
| --- | ---- |
| **L-EQ-01** | ONLINE_OBServed + fixed inputs ⇒ identical `walk_result_hash`. |
| **L-EQ-02** | Independent job order does not change per-job hashes. |
| **L-EQ-03** | Fast path ⇒ passes `EQUIV-*` fixtures vs online. |

---

## 4. Temporal anchors (required fields)

Canonical object per `phase-05-temporal-walk-doctrine.md` §3.1. **All** instants in hash paths use `{unix_ns}` only (**`OCTS-CANON-1`**).

| Field | Required in anchor |
| ----- | ------------------- |
| `tenant_id` | Yes |
| `export_id` | Yes (relaxation only per exploration doctrine) |
| `export_sequence` | **Always Yes** |
| `projection_content_hash` | Yes |
| `snapshot_unix_ns` | Yes |
| `graph_as_of_unix_ns` | Yes |

---

## 5. Index epoch semantics

| Event | `index_epoch` |
| ----- | ------------- |
| Build start | unchanged |
| Validate pass | unchanged |
| Publish commit | `+= 1` |
| Failed publish | unchanged |
| Rollback | **FORBIDDEN** silently — requires new corrective job with receipt |

---

## 6. Snapshot guarantees

| Guarantee | Mechanism |
| --------- | --------- |
| No phantom edges | Import hash lock |
| No missing edges mid-walk | Single snapshot pinned for entire walk |
| Superseded edges absent | P04 export rules + G-P05-TEMP-01 |

---

## 7. Replay blockers (hard fail conditions)

| Code | Condition |
| ---- | --------- |
| `RB-01` | `projection_content_hash` mismatch vs bytes |
| `RB-02` | `policy_hash` mismatch |
| `RB-03` | `pinned_index_epoch` not committed |
| `RB-04` | `octs_schema_version` unsupported |
| `RB-05` | Observed hop dangling evidence |

---

## 8. Async permutation legality

**Permitted:** completing walk job B before A when independent.  
**Forbidden:** splitting **one** walk across workers without coordinator (FS-REM-01).

---

## 9. Read barriers

| Reader | MUST respect |
| ------ | ------------ |
| Authoritative walk store | `execution_partition != exploration` default |
| Certification pack builder | exclude exploration unless explicit audit mode |

---

## 10. Telemetry hash separation

All timing / host / queue depth fields: **TELEMETRY-EXCLUDED** from `walk_result_hash` and `index_content_hash` unless explicitly listed in rare hashed diagnostics (default none).

---

## 11. Deterministic verification mode

Environment flag **`OCTS_VERIFICATION_MODE=strict`**: enables all replay blockers as hard errors; used in CI and certification.

---

## 12. Cross-reference to CI gates

See **`phase-05-verification-gates-doctrine.md`** IDs **G-P05-REPLAY-***, **G-P05-REPLAY-IDX-***, **G-P05-HASH-***.

---

## 13. Closure status

All **P0** replay / anchor / canonicalization items are **closed** in doctrine (`phase-05-spec-gap-matrix.md` §Resolved P0). Remaining work is **pytest harness implementation** per `phase-05-ci-enforcement-architecture.md` — not a spec gap.
