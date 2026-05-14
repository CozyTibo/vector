# Phase 05 — Verification gates doctrine (**G-P05-***)

**Normative step:** **22**. **Freeze bundle:** **FF-5**.  
**Depends on:** All prior OCTS doctrines; **must not** duplicate Phase 04 gates except where extended.

---

## 1. Constitutional intent

Enumerate **CI-enforceable** oracles that **mechanically reject** constitutional violations, hash drift, import leakage, exploration defaults, and ranking smuggling.

---

## 2. Explicit anti-goals

- Gates that require human judgment to pass.  
- Gates that scan production DB without deterministic fixtures.  
- Duplicating P04 gate text in full (link + delta only).

---

## 3. Gate ID registry

| ID | Name | Focus |
| --- | -------------- | ----- |
| **G-P05-CANON-01** | Canonical golden vectors | `OCTS-CANON-1` byte-identical outputs |
| **G-P05-CANON-02** | Idempotency whitespace | Same logical JSON → same `body_identity_hash` |
| **G-P05-CANON-03** | NFC equivalence | Precomposed vs decomposed Unicode |
| **G-P05-IMPORT-01** | Import subset | Traversable ⊆ authoritative export edges. |
| **G-P05-IMPORT-02** | Forbidden tokens | Extends P04 forbidden topology token scan to walk ingress. |
| **G-P05-TEMP-01** | Validity + sequence | Half-open intervals + `export_sequence` monotonicity + supersession. |
| **G-P05-TEMP-02** | Anchor round-trip | Replay loads anchor bytes identically. |
| **G-P05-EXP-01** | Exploration default | API defaults `exploration_mode=false`. |
| **G-P05-EXP-02** | Partition isolation | Physical + logical isolation per `phase-05-exploration-mode-doctrine.md` §14. |
| **G-P05-HASH-01** | Walk hash recompute | Golden JSON → hash. |
| **G-P05-HASH-02** | Telemetry separation | Telemetry mutation does not change hash. |
| **G-P05-SCHEMA-01** | JSON Schema closure | Request/response validate against `schemas/*.schema.json`. |
| **G-P05-ANTI-01** | Forbidden cognition keys | Pattern scan on canonical bodies. |
| **G-P05-OVD-01** | Observed binding | Observed hops have authority_binding. |
| **G-P05-OVD-02** | Derived flags | Derived execution sets flags in result body. |
| **G-P05-MG-01** | Neighbor order | Golden neighbor expansion order bytes. |
| **G-P05-MG-02** | Fingerprint uniqueness | Collision detector. |
| **G-P05-POL-01** | Policy schema | JSON Schema validation. |
| **G-P05-POL-02** | Sync caps | POST rejects over-cap policies on sync path. |
| **G-P05-HR-01** | Fingerprint recompute | Envelope → fingerprint law. |
| **G-P05-HR-02** | Dangling evidence | Injection test fails. |
| **G-P05-DIAG-01** | Enum exhaustiveness | All enums known. |
| **G-P05-DIAG-02** | Cycle vectors | Golden cycles. |
| **G-P05-IDX-01** | Index hash | Double-run rebuild hash match. |
| **G-P05-IDX-02** | Lineage scan | Missing lineage fails. |
| **G-P05-JOB-01** | Index job FSM | Illegal transitions absent. |
| **G-P05-JOB-02** | Crash between phases | Recover deterministic. |
| **G-P05-RT-01** | Engine determinism | 100-run equality. |
| **G-P05-RT-02** | Memory bound | Diagnostic stable at cap. |
| **G-P05-API-01** | HTTP + generated OpenAPI | Generated from `schemas/`; contract tests. |
| **G-P05-API-02** | RBAC | Negative authz. |
| **G-P05-IDEM-01** | HTTP idempotency | Concurrent key tests. |
| **G-P05-IDEM-02** | Worker duplicate delivery | Simulated duplicate ack. |
| **G-P05-REPLAY-WALK-01** | Walk replay nightly | Sampled archive replay. |
| **G-P05-REPLAY-WALK-02** | Edge mutation sensitivity | Predictable hash delta. |
| **G-P05-REPLAY-IDX-01** | Index double-run | Hash match. |
| **G-P05-REPLAY-IDX-02** | Lineage corruption | Deterministic fail. |
| **G-P05-EQUIV-01** | Fast-path online | Same hash. |
| **G-P05-EQUIV-02** | Nightly dual strategy | `warn` on PR; `hard_fail` on `release/*` per CI arch. |
| **G-P05-EQUIV-03** | No floats in canonical | Static scan. |
| **G-P05-RANK-01** | Rank-forbidden scan | Reject score-like numeric maps on edges in OCTS tables/APIs. |
| **G-P05-TVER-01** | Tenant slice schema | Golden aggregate JSON for `org_graph_traversal` slice. |
| **G-P05-CP-01** | Control plane RBAC | Route matrix deny-by-default. |
| **G-P05-ECO-01** | Max out-degree | Hostile hub fixture threshold. |
| **G-P05-MIG-01** | Schema bundle hash | Alembic heads + schema files digest matches manifest. |
| **G-P05-LEGAL-01** | Active P0 empty | `phase-05-spec-gap-matrix.md` §Active P0 must be empty before STAGE-Z. |
| **G-P05-ENG-01** | Engine id | `engine_build_id` matches embedded git metadata. |
| **G-P05-CLOSE-01** | Closure pack | **`OCTS-CERT-PACK-1`** verify per `phase-05-certification-pack-format.md`. |

**Severity:** Defaults per `phase-05-ci-enforcement-architecture.md` §4.

**Topology:** Stage graph, waiver file path, fixture root — **`phase-05-ci-enforcement-architecture.md`** (authoritative).

---

## 3.1 Waiver file

**Path:** `DOCS/cortex/05-traversal/waivers/verification_waivers.yaml` (committed, reviewed).

---

## 4. Deterministic semantics

Gate harness **MUST** run with `OCTS_VERIFICATION_MODE=strict` in CI for `hard_fail` gates.

---

## 5. Replay semantics

Gates validate replay jobs produce **identical** classification pass/fail as inline engine on fixtures.

---

## 6. Temporal semantics

**G-P05-TEMP-01** **MUST** cover: half-open validity, supersession, **`export_sequence`** monotonicity, and instant encoding **`unix_ns`** per **`OCTS-CANON-1`** (no RFC3339 in hashed bodies).

---

## 7. Provenance semantics

Gates that inspect receipts **MUST** use canonical parser shared with production.

---

## 8. Serialization contracts

Golden vectors **MUST** load only from **`backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/`** (see **`phase-05-ci-enforcement-architecture.md`** §7).

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-G-01** | Gate skipped in CI without waiver entry in `DOCS/cortex/05-traversal/waivers/verification_waivers.yaml` with valid `expires_unix_ns`. |
| **FS-G-02** | Two definitions of same gate ID in different files without version note. |

---

## 10. Verification implications

This file **is** the verification implication registry; step-specific doctrines reference IDs here only.

---

## 11. Abuse scenarios

| Abuser | Attack | Gate |
| ------ | ------ | ---- |
| Phase 07 | Smuggle ranking | **G-P05-RANK-01** |

---

## 12. Negative examples

**ILLEGAL waiver:** “too slow, skip G-P05-RT-01” without remediation plan id.

---

## 13. CI oracle expectations

Gate execution **MUST** follow **`phase-05-ci-enforcement-architecture.md`**. Implementations **MUST** wire pytest modules before claiming **operational** CI enforcement; until wired, **normative** gate law is still **Frozen** at the specification layer per `phase-05-spec-gap-matrix.md`.
