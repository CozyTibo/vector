# Phase 05 — Traversal vs reasoning doctrine

**Normative step:** **5**. **Freeze bundle:** **FF-1**.  
**Depends on:** `phase-05-anti-goals-doctrine.md`, `phase-05-normative-index.md`.

---

## 1. Constitutional intent

Define the **output algebra** for OCTS: **only** structural types (graph-shaped facts, diagnostics, hashes, telemetry). **MUST** make it impossible for a consumer to treat a walk as a “conclusion object” without adding Phase 06+ logic outside OCTS.

---

## 2. Explicit anti-goals

- Natural language **explanations** of “why this path.”  
- Scoring paths by “utility” or “business value.”  
- Interpreting edge types as **causal** (only **typed structural labels** allowed).

---

## 3. Formal terminology

| Type class | Examples allowed in `walk_result.body` |
| ---------- | -------------------------------------- |
| **Structural** | `vertices[]`, `edges[]`, `hop_receipts[]`, `diagnostics`, `termination_reason` |
| **Hashes** | `walk_result_hash`, `policy_hash`, `projection_content_hash` |
| **Telemetry** | timings, counters — excluded from hashes |
| **Reasoning-class** | **FORBIDDEN** — any string field not in closed enum lists defined by contracts |

All string enums **MUST** be closed; open-ended `string` fields are **FORBIDDEN** except `opaque_request_id` (UUID format) and `error_code`.

---

## 4. Deterministic semantics

**RULE TVR-01:** Parser for walk results **MUST** be **total** for valid inputs: unknown fields → **reject** in strict mode, **strip** in legacy mode (legacy **MUST NOT** be default for new APIs).  
**RULE TVR-02:** Enum expansion requires **policy_hash** version bump.

---

## 5. Replay semantics

Reasoning-class field absence is **not** optional — gates verify **schema closure**. Replay compares **only** structural + hash fields per walk result contract.

---

## 6. Temporal semantics

**Allowed:** `t_as_of`, `validity_interval` pairs on edges, `snapshot_id`. **Forbidden:** “likely next event time,” “estimated delay.”

---

## 7. Provenance semantics

Provenance is **reference-only**: ids + types + fingerprints — not “meaning.”

---

## 8. Serialization contracts

OpenAPI for walk APIs **MUST** be **generated** from **`DOCS/cortex/05-traversal/schemas/*.schema.json`** — same files validate requests in CI (**`G-P05-SCHEMA-01`**, **`G-P05-API-01`**).

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-TVR-01** | Free-text `notes` on walk result. |
| **FS-TVR-02** | `edge_explanation` string. |
| **FS-TVR-03** | Dynamic keys (`ext_*`) in canonical body. |

---

## 10. Verification implications

- **G-P05-SCHEMA-01:** JSON Schema validation against golden fixtures.  
- **G-P05-ANTI-01:** Overlaps anti-goals pattern scan.

---

## 11. Abuse scenarios

| Consumer | Abuse | Defense |
| -------- | ----- | ------- |
| Admin UI | Render walk JSON as Markdown narrative | Policy outside OCTS; data model still blocks stored narratives. |
| LLM wrapper | Serialize graph to prose in OCTS | API rejects non-schema output. |

---

## 12. Negative examples

**ILLEGAL:**

```json
{ "why_this_path": "Shortest communication path between IC and EM" }
```

**LEGAL:**

```json
{ "termination_reason": "target_reached", "path_length": 4 }
```

---

## 13. CI oracle expectations

- Contract tests verifying **closed enum** exhaustiveness.  
- Fuzzing canonical JSON decoder with random keys → 100% reject in strict mode.
