# Phase 05 — Exploration mode doctrine

**Normative step:** **11**. **Freeze bundle:** **FF-3**.  
**Depends on:** `phase-05-anti-goals-doctrine.md`, `phase-05-walk-policy-doctrine.md`, `phase-05-walk-result-contract.md`.

---

## 1. Constitutional intent

**Mechanically isolate** non-authoritative traversals: separate storage namespace, separate API defaults, explicit flags — **MUST NOT** allow “silent exploration.”

---

## 2. Explicit anti-goals

- Default-on exploration for admin or API.  
- Writing exploration results to certification archives.  
- Mixing exploration receipts into authoritative **walk_audit** tables without partition key.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **exploration_mode** | Boolean request flag; when true, **partition_id = `explore:` + walk_id**. |
| **Read barrier** | Authoritative readers **MUST** filter `partition_id` starting with `explore:` unless `include_exploration=true` (admin-only, audited). |

---

## 4. Deterministic semantics

**RULE EX-01:** `exploration_mode=true` **MUST** force `walk_result.body.execution_partition="exploration"` in canonical body (included in `walk_result_hash`).  
**RULE EX-02:** Wildcard hop filters **ALLOWED** only when `exploration_mode=true`.

---

## 5. Replay semantics

Exploration walks **MUST** be replayable but **MUST** carry **`non_authoritative=true`** in result body (hashed).

---

## 6. Temporal semantics

`relaxed_anchor=true` in policy **MAY** omit **`export_id`** only if **`export_sequence` + `projection_content_hash` + both `unix_ns` objects** remain present and valid. **FORBIDDEN:** omit `export_sequence`.

---

## 7. Provenance semantics

All hop receipts in exploration **MUST** set `partition=exploration`.

---

## 8. Serialization contracts

`execution_partition` enum: `"authoritative"` | `"exploration"` | `"derived_audit"` — canonical string values.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-EX-01** | `exploration_mode=false` with wildcard hop class. |
| **FS-EX-02** | Exploration walk without `non_authoritative=true` in hash body. |
| **FS-EX-03** | API default `exploration_mode=true`. |
| **FS-EX-04** | Cache key without `explore` / `auth` prefix. |

---

## 10. Verification implications

- **G-P05-EXP-01:** API contract tests — default false.  
- **G-P05-EXP-02:** DB constraint — exploration rows rejected on authoritative-only tables.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Product | “Quick insights” toggle | Requires explicit exploration + non_authoritative hash. |

---

## 12. Negative examples

**ILLEGAL:** POST `/walks` without body flag but server sets exploration internally.  
**LEGAL:** explicit JSON `"exploration_mode": true`.

---

## 13. CI oracle expectations

Integration: exploration walk invisible to default aggregate queries in control plane doctrine.

---

## 14. Physical isolation (**contamination constitutionally impossible**)

**RULE EX-P1 — Database:** Tables **`cortex_octs_walk_exploration`** (prefix literal) **MUST** hold exploration rows; **FORBIDDEN** to insert exploration rows into **`cortex_octs_walk_authoritative`**. DB **CHECK** constraint: `partition = 'exploration'`.

**RULE EX-P2 — Cache keys:** Redis keys **MUST** be prefixed `octs:explore:{tenant_id}:` for exploration; authoritative **`octs:auth:{tenant_id}:`**. Shared pool without prefix → **FS-EX-04**.

**RULE EX-P3 — Queues:** Celery queue name **`octs.walk.exploration`** separate from **`octs.walk.authoritative`**; workers **MUST NOT** consume both on one process without static routing manifest declaring dual consumer (default **FORBIDDEN**).

**RULE EX-P4 — Serializers:** Exploration JSON encoder **MUST** be a distinct Python class / TypeScript module path from authoritative encoder (symbol names **`ExplorationOCTSCodec`** vs **`AuthoritativeOCTSCodec`**) to prevent accidental import aliasing.

**RULE EX-P5 — Telemetry:** Exploration telemetry **MUST** land in `exploration_telemetry` sink only (OpenTelemetry exporter name fixed **`octs-exploration`**).

**RULE EX-P6 — Replay exclusion:** Certification pack builder **`G-P05-CLOSE-01`** **MUST** reject any exploration walk bytes under authoritative manifest path (see `phase-05-certification-pack-format.md` §8).

**RULE EX-P7 — Authority downgrade:** Any API that accepts exploration results for operator viewing **MUST** set HTTP header **`X-OCTS-Authority: non-authoritative`** on responses.