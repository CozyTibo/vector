# Phase 05 — Canonicalization profile (**OCTS-CANON-1**)

**Status:** normative — **single source of truth** for byte identity, hashing, and equality.  
**Supersedes:** ad-hoc JSON rules duplicated in `phase-05-normative-index.md` §Canonical OCTS JSON profile — that section is **deprecated**; this file is authoritative.  
**Consumers:** `phase-05-walk-result-contract.md`, `phase-05-idempotency-and-retry-doctrine.md`, `phase-05-walk-api-contracts.md`, all **`G-P05-HASH-***`, **`G-P05-IDEM-***`, replay jobs, certification pack.

---

## 1. Constitutional intent

Eliminate **implementation-defined** serialization. Any two conforming implementations **MUST** produce **identical** canonical bytes for the same logical value, **identical** SHA-256 for the same canonical object, and **identical** idempotency key resolution for the same logical POST body.

---

## 2. Profile identity

| Field | Value |
| ----- | ----- |
| **Profile ID** | `OCTS-CANON-1` |
| **JSON canonicalization ruleset** | RFC 8785 (**JSON Canonicalization Scheme**, JCS) with **OCTS deltas** in §6–§9 below. |
| **Hash** | SHA-256 over **UTF-8 bytes** of the JCS output string, lowercase hex digest, optional prefix `sha256:` where a tagged string is required. |

**INVARIANT CANON-01:** If JCS and an OCTS delta conflict, **OCTS deltas in this document win** for OCTS artifacts only.

---

## 3. UTF-8 and Unicode

1. **Transport encoding:** All OCTS HTTP bodies **MUST** be valid **UTF-8**. Invalid UTF-8 → **`400`** `invalid_utf8` (hard error).  
2. **NFC normalization:** Before **any** comparison, canonicalization, or hash input, every JSON **string value** **MUST** be transformed to **Unicode NFC**. Keys are already ASCII for OCTS schemas.  
3. **Forbidden:** Surrogate halves, noncharacters U+FFFE/U+FFFF in strings that enter canonical bodies. **MUST** reject at validation.

---

## 4. Instant semantics (leap seconds, time zones, same instant)

**RULE TIME-01 — No zone ambiguity:** OCTS **MUST NOT** accept local offsets in canonical bodies. Only **`Z`** suffixed RFC 3339 strings are allowed **outside** hash inputs where human display is required.

**RULE TIME-02 — Hash instant representation:** Every instant that enters **`walk_result_hash`**, **`policy_hash`**, **`temporal_anchor` canonical object**, replay job payloads, or certification pack manifest lines **MUST** be encoded as a JSON object:

```json
{ "unix_ns": 1704067200000000000 }
```

where **`unix_ns`** is a **non-negative integer** count of **nanoseconds** since **Unix epoch 1970-01-01T00:00:00Z**, using **POSIX** clock mapping (leap seconds **MUST NOT** create non-monotonic `unix_ns` in a single process; see §4.1).

**RULE TIME-03 — Same instant, different events:** If two exports seal in the same POSIX `unix_ns`, they **MUST** still differ by **`export_sequence`** (strict monotonicity per tenant). Ordering key is **`(tenant_id, export_sequence)`** lexicographic on `export_sequence` as unpadded decimal integer string for deterministic sort in manifests.

### 4.1 Leap second and non-monotonic clock caveats (closed rule)

**RULE TIME-LS-01:** OCTS runtime **MUST** derive `unix_ns` from the platform clock using **UTC** with POSIX leap-second smear or repeat-second behavior **as implemented by the runtime’s `time.Time` / `datetime` UTC source**, but **MUST** persist **`export_sequence`** from the database **before** emitting `unix_ns` in export headers so that **total order** is **`export_sequence`**, not wall clock alone.

**RULE TIME-LS-02:** Certification and replay comparators **MUST NOT** compare wall-clock strings; they **MUST** compare **`unix_ns` + `export_sequence`** fields only.

---

## 5. JSON Canonicalization Scheme (JCS) application

**Input:** Parsed JSON value (UTF-8 text → AST).

**Output:** A single UTF-8 string, **no** trailing newline, produced by:

1. Parse JSON strictly (**RFC 8259**). **Duplicate keys FORBIDDEN** → **`400`** `duplicate_json_key`.  
2. Apply NFC to all string values (not keys; OCTS keys are ASCII).  
3. Apply **JCS** serialization to the AST.  
4. Apply **OCTS deltas** (§6–§9) as post-pass transforms on the JCS output string **or** equivalently on the AST before final JCS — implementations **MUST** be bitwise-identical to reference golden vectors in `octs_golden_vectors/v1/canonicalization/`.

**INVARIANT CANON-02:** `octs_canonical_json(body) → bytes` is a **total function** for valid inputs and **MUST** error on invalid inputs (no silent repair beyond NFC).

---

## 6. OCTS deltas on top of JCS

### 6.1 Numbers

- **Integers:** JSON integers only where schema requires integer.  
- **Floating-point:** **FORBIDDEN** in any OCTS canonical body that participates in a hash unless a schema explicitly allows a fixed binary IEEE754 representation — **no** such schema exists in **OCTS-CANON-1** v1. **`400`** if float detected.

### 6.2 Objects

- Keys sorted per JCS (lexicographic UTF-8 codepoint order).

### 6.3 Arrays

- Order is **significant** unless a schema marks an array **order_invariant**, in which case elements **MUST** be sorted by their **individual canonical JSON strings** ascending.

### 6.4 Omitted vs null

- **`null`:** Only where schema explicitly allows `null`.  
- **Omission:** Optional fields with default **MUST** be omitted when equal to default (defaults table per schema file). If a field has no default, absence and `null` follow **`schemas/*.schema.json`** `oneOf` / `type` rules.

---

## 7. Idempotency body law (**GAP-P0-02 — CLOSED**)

**Chosen rule (single, global):**

**RULE IDEM-01 — Canonical body bytes:** The idempotency comparator for `POST` walk (and any other idempotent OCTS POST) **MUST** compare **only**:

```
body_identity_bytes = UTF8( JCS_OCTS( ParseJSON( raw_request_body_utf8 ) ) )
```

where **`raw_request_body_utf8`** is the **raw HTTP body bytes** decoded as UTF-8 **after** rejecting invalid UTF-8.

**RULE IDEM-02 — No raw-byte compare:** Raw-byte equality **MUST NOT** be used for idempotency (whitespace, key order, and Unicode normalization would false-negative).

**RULE IDEM-03 — Idempotency record stores:** `(tenant_id, idempotency_key_hash, body_identity_hash)` where:

- `idempotency_key_hash = SHA256( UTF8( NFC(Idempotency-Key header value) ) )`  
- `body_identity_hash = SHA256( body_identity_bytes )`

**RULE IDEM-04 — Mismatch:** Same `Idempotency-Key` + different `body_identity_hash` → **`409`** `idempotency_key_conflict` with **no** mutation.

**RULE IDEM-05 — Match:** Same triple → return **byte-identical** prior response body (same HTTP status), **including** headers that affect caching semantics per API contract.

---

## 8. Hashing law

**RULE HASH-01:** `H_octets(x) = SHA256( x )` where `x` is a byte string.

**RULE HASH-02:** `walk_result_hash = "sha256:" + hex( H_octets( body_identity_bytes( walk_result.hash_body ) ) )` where `hash_body` is the object defined in `phase-05-walk-result-contract.md` **after** substituting all nested instants with `{unix_ns:…}` per §4.

---

## 9. Canonical body comparison (non-hash)

For diff tools: compare **`body_identity_bytes`** of two logical bodies.

---

## 10. Forbidden states

| ID | State |
| -- | ----- |
| **FS-CANON-01** | Float in canonical input. |
| **FS-CANON-02** | Duplicate JSON keys accepted. |
| **FS-CANON-03** | Raw-byte idempotency compare used. |
| **FS-CANON-04** | RFC3339 string inside `hash_body`. |

---

## 11. Verification implications

- **`G-P05-CANON-01`:** Golden vectors: 20 fixtures → canonical string → golden digest.  
- **`G-P05-CANON-02`:** Idempotency: same logical JSON, different whitespace → same `body_identity_hash`.  
- **`G-P05-CANON-03`:** NFC: precomposed vs decomposed Unicode → identical canonical.

---

## 12. CI oracle expectations

Vectors live only under **`backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/canonicalization/`** (see **`phase-05-ci-enforcement-architecture.md`**).

---

## 13. Versioning

Bump **`OCTS-CANON-1`** to **`OCTS-CANON-2`** only via **constitutional amendment** with migration receipts; **`octs_schema_version`** in walk results **MUST** increment.
