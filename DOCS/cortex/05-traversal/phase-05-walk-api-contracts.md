# Phase 05 — Walk API contracts

**Normative steps:** **17**, **18**, **19**, **20** (index replay HTTP shares traversal prefix). **Freeze bundle:** **FF-5**.  
**Depends on:** `phase-05-walk-result-contract.md`, `phase-05-idempotency-and-retry-doctrine.md`, `phase-05-exploration-mode-doctrine.md`, `phase-05-temporal-walk-doctrine.md`.

---

## 1. Constitutional intent

Define **HTTP/admin** contracts for walk submission, polling, and cancellation — with **sync limits** (Step 18) strictly smaller than async/job path.

---

## 2. Explicit anti-goals

- Unbounded synchronous walks.  
- Public unauthenticated walk endpoints (tenant isolation **MUST**).  
- Returning non-canonical JSON field ordering as a contract guarantee (ordering is logical, not wire — clients parse JSON).

---

## 3. Formal terminology

**Authoritative wire shape:** JSON Schema files under **`DOCS/cortex/05-traversal/schemas/`** — starting with **`octs-walk-request-v1.schema.json`**.

**RULE API-0:** OpenAPI **MUST** be **generated** from those schemas (single generator command recorded in `backend/Makefile` or `package.json` when introduced). **Hand-written** OpenAPI **FORBIDDEN** as a source of truth.

| Path (normative — OpenAPI paths MUST match) | Method | Role |
| --------------------------- | ------ | ---- |
| `/admin/tenants/{tid}/cortex/traversal/walks` | POST | Submit walk (sync small or async job). |
| `/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}` | GET | Poll result. |
| `/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}/cancel` | POST | Cooperative cancel. |

**RULE API-ERR:** Error bodies **MUST** be `{"error_code": string, "details": object}` with `details` keys sorted and values only JSON primitives allowed by schema — **no** free text beyond `error_code` enum companion table in schema `description` (not serialized).

Until the generator ships, HTTP handlers **MUST** validate requests against the JSON Schema file using **`jsonschema`** (Python) or equivalent with **`OCTS-CANON-1`** post-parse.

---

## 4. Deterministic semantics

**RULE API-01:** Response body for GET **MUST** include `walk_result` if completed else `status` enum `queued|running|completed|failed|cancelled`.  
**RULE API-02:** `202 Accepted` with `job_id` when async path taken.

---

## 5. Replay semantics

Async completion **MUST** store identical `walk_result` bytes as sync would for same logical inputs.

---

## 6. Temporal semantics

POST body **MUST** include `temporal_anchor` or explicit `inherit_walk_id` per temporal doctrine.

---

## 7. Provenance semantics

Headers `Idempotency-Key` required on POST in strict mode.

---

## 8. Serialization contracts

Error model: `{ "error_code": "…", "details": {…sorted…} }` — `details` only enums/fingerprints.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-API-01** | Sync response for walk exceeding caps (must 413/400 per table). |
| **FS-API-02** | Missing tenant in path. |

---

## 10. Verification implications

- **G-P05-API-01:** OpenAPI contract tests (schemathesis optional).  
- **G-P05-API-02:** RBAC negative tests.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Caller | Huge POST bodies | Size limits + stream reject. |

---

## 12. Negative examples

**ILLEGAL:** 200 OK with full 1M-hop walk synchronously.

---

## 13. CI oracle expectations

HTTP golden files; latency budget tests for sync caps.

### §Sync limits (Step 18)

| Parameter | Max (default strict) |
| --------- | -------------------- |
| `max_hops` | 32 |
| `max_edges_visited` | 10_000 |
| `max_wall_ms` | 150 |
| Request JSON bytes (sync POST body, canonical UTF-8) | 256 KiB |
| Response JSON bytes (sync completed GET/POST, canonical UTF-8) | 256 KiB |

**MUST** return **413** or **`walk_too_large`** when exceeded — engine **MUST NOT** partially return.

---

## 14. Reference implementation (**P05-17** / **P05-18** / **P05-19** / **P05-20**)

**JSON Schema:** `DOCS/cortex/05-traversal/schemas/octs-walk-request-v1.schema.json` — `temporal_anchor` **or** `inherit_walk_id` required (**anyOf**); optional **`expected_walk_result_hash`** (strict pin vs source **`walk_result_hash`**); **Step 19** resolves **`inherit_walk_id`** against the in-memory walk store and pins **`temporal_anchor`** from the completed parent when omitted on the wire.

**OpenAPI (generated):** `DOCS/cortex/05-traversal/schemas/generated/octs-walk-api-v1.openapi.json` — regenerate with `make octs-openapi` (`python -m vector.scripts.generate_octs_walk_openapi`).

**Python:** `vector.domains.cortex.traversal.walk_api_contract` — canonical API error bodies (**RULE API-ERR**), stub completed walk payload builder (**`OCTS_STUB_ENGINE_BUILD_ID`** + replay lineage telemetry when **Step 19** applies), in-memory store, **G-P05-API-01** / **G-P05-API-02** / **G-P05-API-03** static gates; canonical UTF-8 byte measurement helpers + **FS-API-01** violation lists for sync request/response caps (**Step 18**).

**Replay resolution:** `vector.domains.cortex.traversal.walk_replay_contract` — **`prepare_effective_oct_walk_request_v1`**, **`verify_oct_walk_replay_stub_inherit_resolution_static`** (local gate **`octs-walk-replay-stub-inherit-v1`**); errors **`source_walk_not_found`** (**404**), **`source_walk_not_replayable`**, **`replay_input_mismatch`**, **`replay_anchor_mismatch`**, **`replay_hash_mismatch`**.

**Doctrine constants:** `vector.domains.cortex.traversal.walk_policy` — `SYNC_MAX_*` caps including **`SYNC_MAX_REQUEST_JSON_BYTES`** / **`SYNC_MAX_RESPONSE_JSON_BYTES`** (256 KiB each).

**Admin HTTP:** `vector.api.http.routes.admin_octs_walks` — `POST/GET …/cortex/traversal/walks`, `POST …/cancel`, **Step 20** `POST …/cortex/traversal/derived-index/replay-verify` (**`phase-05-index-replay-doctrine.md`**); `async=1` → **202** + `job_id` (sync-only request/response byte caps **not** applied); sync path enforces policy caps + JSON caps → **413** `walk_too_large` with **no** partial success body on violation; completed GET/replay/idempotent POST paths re-check response size; **Step 19** inherit replay runs on the resolved effective request after parent lookup.

**Tests:** `test_phase05_step17_walk_api_contracts.py`, `test_phase05_step18_sync_walk_limits.py`, `test_phase05_step19_walk_replay.py`, `test_phase05_step20_index_replay.py`, `test_admin_octs_walks_step17.py`.
