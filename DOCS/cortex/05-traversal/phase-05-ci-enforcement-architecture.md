# Phase 05 — CI enforcement architecture (**G-P05-***)

**Status:** normative — **gate execution topology**, **CI ordering**, **admission control**, **waiver law**, **oracle determinism**.  
**Pairs with:** `phase-05-verification-gates-doctrine.md` (gate ID registry), `phase-05-runtime-legality-matrix.md`, `phase-05-canonicalization-profile.md`.

---

## 1. Constitutional intent

Make **`G-P05-***` mechanically enforceable** with **zero** ambiguous ownership: which job runs when, what fails the build, what may ship to production, how waivers expire, and how fixtures stay versioned.

---

## 2. Gate execution topology

```
                    ┌──────────────────────────────┐
                    │   OCTS_GATE_ORCHESTRATOR     │
                    │ (canonical verification ext) │
                    └──────────────┬───────────────┘
                                   │
     ┌─────────────────────────────┼─────────────────────────────┐
     ▼                             ▼                             ▼
┌─────────────┐           ┌───────────────┐              ┌────────────────┐
│ STAGE-A     │           │ STAGE-B       │              │ STAGE-C        │
│ static+schema│─────────▶│ unit oracles  │─────────────▶│ replay vectors │
└─────────────┘           └───────────────┘              └────────┬───────┘
                                                                  │
                    ┌─────────────────────────────────────────────┘
                    ▼
           ┌─────────────────┐         ┌──────────────────┐
           │ STAGE-D         │────────▶│ STAGE-E (nightly) │
           │ integration API │         │ EQUIV-02 + soak   │
           └─────────────────┘         └──────────────────┘
```

**STAGE-A — Static + schema (blocking PR):**  
- **`G-P05-SCHEMA-01`**, **`G-P05-ANTI-01`**, **`G-P05-RANK-01`**, **`G-P05-CANON-01..03`**, **`G-P05-IMPORT-02`** (token scan on fixtures only if no DB).  
- **Runtime:** `pytest -q tests/vector/domains/cortex/traversal/test_octs_stage_a.py` (exact path when package exists).

**STAGE-B — Unit oracles (blocking PR):**  
- **`G-P05-MG-01`**, **`G-P05-POL-01`**, **`G-P05-HASH-01`**, **`G-P05-HR-01`**, **`G-P05-DIAG-01`**, **`G-P05-IDX-01`**, **`G-P05-IDX-02`**, **`G-P05-JOB-01`**, **`G-P05-JOB-02`**, **`G-P05-EQUIV-01`**, **`G-P05-WES-01`**, **`G-P05-WES-02`**, **`G-P05-RT-01`**, **`G-P05-RT-02`**, fingerprint recompute, policy hash golden.

**STAGE-C — Replay vectors (blocking PR on OCTS paths):**  
- **`G-P05-REPLAY-WALK-02`**, **`G-P05-REPLAY-IDX-01`**, **`G-P05-REPLAY-IDX-02`** (static double-run + corrupt-lineage gates in `index_replay_contract` + golden derived artifact), **`G-P05-TEMP-01`**, **`G-P05-TEMP-02`**, **`G-P05-OVD-01`**, **`G-P05-EXP-01`**.

**STAGE-D — Integration HTTP (blocking merge to main):**  
- **`G-P05-API-01`**, **`G-P05-API-02`**, **`G-P05-API-03`** (OpenAPI artifact + admin traversal integration tests + sync walk limit static gate), **`G-P05-IDEM-01`**, **`G-P05-EXP-02`**, **`G-P05-CP-01`**.

**STAGE-E — Nightly (blocking release / `release` branch only):**  
- **`G-P05-REPLAY-WALK-01`** (sampled archive), **`G-P05-EQUIV-02`**, **`G-P05-RT-01`** extended / large-graph stress (beyond the PR static 100× harness), **`G-P05-ECO-01`**, **`G-P05-ECO-02`**, **`G-P05-ECO-03`**.

**STAGE-Z — Closure bundle (blocking tag `octs-v*`):**  
- **`G-P05-CLOSE-01`** runs **after** STAGE-A–D all green on the **same** commit SHA; **MUST** load certification pack bytes per `phase-05-certification-pack-format.md`.

---

## 3. CI stage ordering (hard)

| Order | Stage | May run if |
| ----- | ----- | ---------- |
| 1 | A | clean checkout |
| 2 | B | A = green |
| 3 | C | B = green |
| 4 | D | C = green **and** docker services profile `octs-ci` up |
| 5 | E | merge to `main` OR cron OR manual `workflow_dispatch` |
| 6 | Z | release tag + A–D green on tag SHA |

**INVARIANT CI-01:** **MUST NOT** parallelize stages across **different** SHAs for the same release tag.

---

## 4. `hard_fail` vs `warn`

| Gate | Default severity |
| ---- | ---------------- |
| All **`G-P05-***` except below** | `hard_fail` |
| **`G-P05-EQUIV-02`** | `warn` on PR; **`hard_fail`** on `release/*` and version tags |
| **`G-P05-REPLAY-WALK-01`** | `warn` on PR; **`hard_fail`** nightly |

**Promotion rule:** Any gate may be promoted from `warn` → `hard_fail` for all branches by **constitutional amendment** recorded in `phase-05-spec-gap-matrix.md` §Amendments.

---

## 5. Waiver mechanics

**File:** `DOCS/cortex/05-traversal/waivers/verification_waivers.yaml`

**Schema (normative fields):**

```yaml
waivers:
  - gate_id: "G-P05-EQUIV-02"
    ticket: "https://linear.app/…/OCTS-123"
    reason: "Fast path not shipped; tracked."
    expires_unix_ns: 1735689600000000000
    branches_allowlist: ["main"]
```

**RULE W-01:** A waiver **MUST** name **`gate_id`**, **`ticket`**, **`expires_unix_ns`**, **`branches_allowlist`**.  
**RULE W-02:** Expired waiver → gate **MUST** run as **`hard_fail`**.  
**RULE W-03:** **`G-P05-CLOSE-01`** **MUST NOT** be waived on tags `octs-v*`.  
**RULE W-04:** Waivers **MUST** be committed to **default branch** within **24h** of first skip or CI **MUST** fail (`FS-G-01`).

---

## 6. Oracle determinism

**RULE OR-01:** Every oracle **MUST** seed RNG (if any) with `SHA256(gate_id + fixture_name + fixture_version)` first 8 bytes as uint64.  
**RULE OR-02:** Oracles **MUST NOT** read wall clock except through **`unix_ns`** fixture clock injection interface.  
**RULE OR-03:** Filesystem order **MUST NOT** affect outcomes; fixture enumeration sorted by **UTF-8 path**.

---

## 7. Fixture and golden vector lifecycle (**GAP-P0-03 — CLOSED**)

**Canonical root (single home):**  
`backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/`

| Subpath | Content |
| ------- | ------- |
| `canonicalization/` | JCS+NFC golden pairs |
| `walks/` | Full walk request/response golden |
| `walk_execution_strategy/` | **G-P05-EQUIV-01** / **G-P05-WES-01** / **G-P05-WES-02** — fast-path hash equivalence + policy/strategy gates (**P05-15**) |
| `indexes/` | Derived index rebuild golden |
| `index_build_job/` | Index build job FSM audit golden (**P05-14**) |
| `manifests/` | Ordered file list + `sha256` per file for pack tests |

**Promotion rules:**  
- **Add:** PR must include **STAGE-A** vector update + **manifest** line append **sorted**.  
- **Mutate:** **FORBIDDEN** in place — bump `v2/` subtree; `v1` immutable after tag `octs-vectors-v1`.  
- **CI load:** `OCTS_VECTOR_ROOT` env defaulting to the path above; **MUST** be absolute in CI.

---

## 8. Runtime admission gates (deploy)

Before any process flag **`OCTS_RUNTIME_ADMITTED=true`**:

| Precondition | Gate / check |
| ------------ | ------------ |
| FF-4 for code touching Steps 1–15 | policy table in `phase-05-runtime-legality-matrix.md` |
| FF-5 for persistence Steps 13–26 | same |
| DB migrations applied | **`G-P05-MIG-01`** (schema hash matches `expected_schema_bundle_hash` in pack) |
| `OCTS_VERIFICATION_MODE=strict` in prod | **FORBIDDEN** default — prod uses **`standard`**; **`strict`** only CI/cert |

**`G-P05-MIG-01`:** Compare Alembic heads hash against pack manifest `schema_migrations_sha256`.

---

## 9. Failure propagation

**RULE FP-01:** First `hard_fail` **MUST** abort stage; later stages **MUST NOT** run (no partial green).  
**RULE FP-02:** STAGE-E failure **MUST** open incident + **block** release promotion bot.

---

## 10. Corruption-specific gate bundles

| Bundle | Gates |
| ------ | ----- |
| **Exploration contamination** | **`G-P05-EXP-01`**, **`G-P05-EXP-02`**, **`G-P05-CLOSE-01`** slice |
| **Temporal corruption** | **`G-P05-TEMP-01`**, **`G-P05-TEMP-02`**, anchor golden |
| **Canonicalization corruption** | **`G-P05-CANON-01..03`**, **`G-P05-HASH-02`** |
| **Equivalence corruption** | **`G-P05-EQUIV-01`**, **`G-P05-EQUIV-03`** |

---

## 11. Forbidden states

| ID | State |
| -- | ----- |
| **FS-CI-01** | Gate runs on wrong vector root without `OCTS_VECTOR_ROOT` set in CI. |
| **FS-CI-02** | STAGE-D uses production DB. |
| **FS-CI-03** | Missing waiver for skipped `hard_fail` gate. |

---

## 12. Negative examples

**ILLEGAL:** skipping **`G-P05-IMPORT-01`** in CI because “slow” without waiver + expiry.

---

## 13. Versioning

Bump **`OCTS-CI-ARCH-1`** only when topology changes; record in certification pack manifest.
