# Phase 05 — Traversal equivalence doctrine

**Normative step:** **21**. **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-walk-replay-doctrine.md`, `phase-05-runtime-execution-model.md`, `phase-05-walk-execution-strategy-doctrine.md`.

---

## 1. Constitutional intent

Define **equivalence laws** for double-run, cross-build, and async scheduling so “same inputs” has a **single** mathematical meaning for hashed artifacts.

---

## 2. Explicit anti-goals

- Declaring equivalence without pinned `engine_build_id` when nondeterminism exists.  
- Hiding known async ordering effects.

---

## 3. Engine identity (`engine_build_id`) — **GAP-P0-05 CLOSED**

**Source of truth:** the **git commit** that produced the **`vector`** binary (or wheel) executing the walk / replay / pack builder.

**Normative forms (exactly one applies):**

| Form | Pattern | When allowed |
| ---- | ------- | -------------- |
| **Release** | `git:` + **40** lowercase hex SHA-1 object name | CI, staging, production |
| **Local dev** | `dev:unknown` | **Only** when `OCTS_DEV_ENGINE_ID=1` env set AND pack flag `dev_pack=true` in manifest extension file (never in `OCTS-CERT-PACK-1` release manifest) |

**RULE ENG-01:** `engine_build_id` **MUST** appear in replay job receipts, certification `manifest.json`, and equivalence fixture headers.

**RULE ENG-02 — Collision:** Two different binaries **MUST NOT** share the same `git:` digest; if CI detects mismatch between reported `engine_build_id` and `vector.__git_sha__` (or `importlib.metadata`), **`G-P05-ENG-01` fails**.

**RULE ENG-03 — Unavailable:** If git metadata absent in dev without `OCTS_DEV_ENGINE_ID=1`, runtime **MUST** refuse **authoritative** walks (`503` `engine_identity_unavailable`).

**RULE ENG-04 — Replay:** Historical replay **MUST** record **both** `engine_build_id_original` and `engine_build_id_replay`; hashes compare only structural bodies — engine ids in **telemetry** outside `walk_result_hash`.

---

## 4. Equivalence laws (formal)

| Law | Statement |
| --- | --------- |
| **L-EQ-01 (Walk hash equivalence)** | For `exploration_mode=false`, `ONLINE_OBSERVED`, fixed seed graph, fixed anchor/policy: two runs **MUST** yield identical `walk_result_hash`. |
| **L-EQ-02 (Async permutation legality)** | Unordered collection of **independent** walk jobs may complete in any order; **each** job’s artifact hash law unchanged. |
| **L-EQ-03 (Fast-path)** | If enabled, satisfies execution strategy doctrine obligation suite `EQUIV-*`. |

---

## 5. Deterministic semantics

**RULE TE-01:** Any introduced randomness (e.g., UUID for `walk_id`) **MUST NOT** enter `walk_result_hash` unless explicitly listed in hash body (it is **not** listed — only structural content).

---

## 6. Replay semantics

Replay job is the **oracle** for equivalence: online engine vs replay harness must match.

---

## 7. Temporal semantics

Changing **`export_sequence`** ordering rules changes equivalence class — amendments **MUST** bump `octs_schema_version`.

---

## 8. Provenance semantics

Equivalence certificates attach to certification pack per `phase-05-certification-pack-format.md`.

---

## 9. Serialization contracts

Equivalence test vectors stored as canonical JSON + expected hashes per **`OCTS-CANON-1`** (`phase-05-canonicalization-profile.md`).

---

## 10. Forbidden states

| ID | State |
| -- | ----- |
| **FS-TE-01** | Same inputs, different hash, no `engine_build_id` mismatch explanation. |
| **FS-TE-02** | Fast path enabled without `EQUIV-*` passing. |

---

## 11. Verification implications

- **G-P05-EQUIV-01** (shared with execution strategy).  
- **G-P05-EQUIV-03:** Cross-OS float ban enforcement (already banned).  
- **`G-P05-ENG-01`:** `engine_build_id` matches embedded git metadata.

---

## 12. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| CI flake | Order-dependent hash | Laws require sorting where multisets used. |

---

## 13. Negative examples

**ILLEGAL:** “equivalent modulo timestamps” for walk hash compare.

---

## 14. CI oracle expectations

Run equivalence suite on every PR touching `vector.domains.cortex.traversal*`.
