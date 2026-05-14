# Phase 05 — Temporal walk doctrine

**Normative step:** **7**. **Freeze bundle:** **FF-2**.  
**Depends on:** `phase-04-temporal-validity-and-revocation-doctrine.md`, `phase-05-multigraph-model-doctrine.md`, `phase-05-normative-index.md`, `phase-05-canonicalization-profile.md`.  
**GAP-P0-01:** **CLOSED** in this document.

---

## 1. Constitutional intent

Pin **export identity**, **monotonicity**, **walk-time validity**, and **replay anchors** so temporal behavior is **total-order**, **replay-stable**, and **free of wall-clock ambiguity** in hashed bodies.

---

## 2. Explicit anti-goals

- Heuristic “active at roughly now.”  
- Mixing API receive time into **`graph_as_of_unix_ns`** without explicit request field.  
- Implicit non-UTC clocks in canonical bodies.  
- Using **only** `projection_content_hash` without **`export_sequence`** as an ordering key.

---

## 3. Formal terminology

### 3.1 `temporal_anchor` (authoritative tuple)

**REQUIRED keys (sorted for JSON display; hashed per `OCTS-CANON-1`):**

| Key | Type | Meaning |
| --- | ---- | ------- |
| `tenant_id` | string | UUID string lowercase — tenant owning the walk. |
| `export_id` | string | UUID string lowercase — **one** Phase 04 `OrgGraphProjectionV1` export job instance. |
| `export_sequence` | integer | **uint64** strict-monotonic **per `tenant_id`** across **committed** exports; allocated by export commit transaction (**never** reused). |
| `projection_content_hash` | string | `sha256:` + 64 hex — hash of export bytes per Phase 04 doctrine. |
| `snapshot_unix_ns` | object | `{ "unix_ns": <uint64> }` per **`OCTS-CANON-1`** — instant the export was **sealed** (commit time of export row), **UTC POSIX**. |
| `graph_as_of_unix_ns` | object | `{ "unix_ns": <uint64> }` — instant used for **half-open validity** tests on org links for this walk. |

**INVARIANT TA-01:** `export_sequence` **MUST** increase by **exactly 1** per new committed export per tenant (no gaps, no reuse). Gap or reuse → **`500`** `export_sequence_corruption` and **G-P05-TEMP-01** failure.

**INVARIANT TA-02:** `(tenant_id, export_sequence)` is a **global identity** for an export snapshot for that tenant.

### 3.2 Snapshot linearization (total order)

For any two exports **A** and **B** for the same `tenant_id`:

1. Compare `export_sequence` as integers.  
2. If equal → **ILLEGAL STATE** `FS-TW-SEQ` (DB uniqueness violation).  
3. **Do not** use `snapshot_unix_ns` for tie-break (sequences prevent ties).

**Cross-tenant:** no ordering required.

### 3.3 Concurrent exports

**RULE CONC-01:** Two concurrent export transactions **MUST** serialize **`export_sequence`** allocation via **`SELECT … FOR UPDATE`** on the tenant’s sequence row (or equivalent) so **no** duplicate sequence is committed.

**RULE CONC-02:** If an export transaction **rolls back**, it **MUST NOT** consume a sequence number.

### 3.4 Snapshot conflict behavior

If a walk references `(tenant_id, export_sequence, projection_content_hash)` where recomputed hash from stored bytes ≠ `projection_content_hash` → **`409`** `projection_hash_mismatch` — **MUST NOT** walk.

If `export_id` UUID does not match the row for `(tenant_id, export_sequence)` → **`409`** `export_identity_mismatch`.

### 3.5 Replay legality under concurrent exports

**RULE RPL-01:** A replay job **MUST** pin the full **`temporal_anchor`** object bytes from the original walk.  
**RULE RPL-02:** Replay **MUST** reject if the stored export bytes for that `(tenant_id, export_sequence)` were **superseded** (deleted/archived) unless `replay_mode` is exploration-only per `phase-05-walk-replay-doctrine.md`.

### 3.6 Half-open validity on org links

**Half-open validity:** edge eligible iff `valid_from_unix_ns <= graph_as_of_unix_ns < valid_to_unix_ns` where `valid_to_unix_ns` may be absent meaning **+∞** only if Phase 04 export uses explicit **`valid_to_open`** boolean; else **`GAP-P1-03`** resolution applies: **MUST** emit explicit `valid_to_unix_ns` sentinel **`UINT64_MAX`** in export JSON for open-ended (canonical int, not null).

### 3.7 Supersession precedence

**RULE SUP-01:** If Phase 04 marks link superseded, export **MUST** exclude it from traversable set. OCTS **MUST NOT** resurrect.  
**RULE SUP-02:** Replay against older `export_sequence` **MAY** still see the edge; replay against newer sequence **MUST NOT** — deterministic with pinned anchor.

### 3.8 Same calendar timestamp, different exports

**Covered** by strictly monotonic `export_sequence`; `snapshot_unix_ns` **MAY** tie — ordering is **not** by wall clock.

### 3.9 Leap seconds and time zones

All `unix_ns` fields follow **`OCTS-CANON-1` §TIME**. **No** local offsets in OCTS canonical bodies.

---

## 4. Deterministic semantics

**RULE TW-01:** Walk request **MUST** include full **`temporal_anchor`** **or** `inherit_anchor_from_walk_id` (which copies anchor bytes exactly). **FORBIDDEN:** implicit “latest export” in `OCTS_VERIFICATION_MODE=strict`.

**RULE TW-02:** `graph_as_of_unix_ns` **MUST** satisfy `snapshot_unix_ns - MAX_CLOCK_SKEW_NS <= graph_as_of_unix_ns <= snapshot_unix_ns + MAX_CLOCK_SKEW_NS` where `MAX_CLOCK_SKEW_NS = 300_000_000_000` (5 minutes) unless policy sets stricter bound in **`policy_hash`**.

---

## 5. Replay semantics

**REPLAY REQUIREMENT TW-01:** Replayed walk **MUST** use **`temporal_anchor`** byte-identical to original canonical JSON.

**REPLAY REQUIREMENT TW-02:** If export bytes at `(tenant_id, export_sequence)` changed but hash matches (collision) → **stop the world** — treat as **`500`** `projection_hash_second preimage` and **G-P05-TEMP-01** failure.

---

## 6. Temporal semantics

**INVARIANT:** `invalid_edge_at_t` **MUST** fire when a hop would use an edge outside validity — **no** silent skip unless policy **`skip_invalid_edges=true`** (default **false**).

---

## 7. Provenance semantics

Hop receipts **MUST** copy **`valid_from_unix_ns`**, **`valid_to_unix_ns`** (or sentinel), **`export_sequence`**, **`edge_fingerprint`**.

---

## 8. Serialization contracts

**`temporal_anchor`:** canonical per **`OCTS-CANON-1`**; **FORBIDDEN** to include ISO-8601 strings inside objects that enter **`walk_result_hash`**.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-TW-01** | Missing `export_sequence` in authoritative walk. |
| **FS-TW-02** | Server `now()` used as `graph_as_of` without request field in strict mode. |
| **FS-TW-03** | Same `walk_id` reused with different anchor. |
| **FS-TW-SEQ** | Duplicate `(tenant_id, export_sequence)` committed. |

---

## 10. Verification implications

- **`G-P05-TEMP-01`:** Validity arithmetic + supersession + sequence monotonicity fixtures.  
- **`G-P05-TEMP-02`:** Anchor round-trip + concurrent export simulation (two workers, one sequence winner).

---

## 11. Abuse scenarios

| Downstream | Abuse | Defense |
| ---------- | ----- | ------- |
| Phase 06 | Stretch intervals | Only `graph_as_of_unix_ns` from anchor; no stretch API. |

---

## 12. Negative examples

**ILLEGAL:** anchor with only `projection_content_hash` and no `export_sequence`.

**LEGAL:** full anchor including `export_sequence` and both `unix_ns` objects per §3.1.

**ILLEGAL:** `export_sequence` reused after successful export commit (sequence corruption).

---

## 13. CI oracle expectations

Golden anchors under `octs_golden_vectors/v1/temporal/`; property tests for `export_sequence` monotonicity with rollback.
