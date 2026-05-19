# Phase 08.5 — Closure gates & certification

**Status:** normative.  
**Implements:** Step 36 · **G-P085-CLOSE-01**.

---

## **G-P085-CLOSE-01**

Certification pack: **`CESP-CERT-PACK-1`** (gzip tar).

| File | Content |
| ---- | ------- |
| `manifest.json` | format, `PHASE085_PROGRAM_FREEZE_VERSION`, git sha |
| `gate_results.json` | all **G-P085-*** results |
| `golden_tenant_slice.json` | maturity + density snapshot |
| `soak_summary.json` | 7d operational metrics |
| `readiness_checklist.json` | R1–R15 |
| `policy_thresholds.json` | θ_ret, θ_tcre, T_stall, caps |

Verification: `verify_cesp_cert_pack_v1(bytes)` in CI.

---

## Phase 08.5 completion criteria

| # | Criterion |
| - | --------- |
| 1 | Steps **1–36** doctrine **Frozen** |
| 2 | All **hard_fail** **G-P085-*** wired |
| 3 | Migration **0082+** applied |
| 4 | Watchdog in beat schedule |
| 5 | Admin cockpit surfaces **≥ 12/19** shipped |
| 6 | Golden tenant **OPERATIONAL_ALIVE** |
| 7 | **CESP-CERT-PACK-1** in CI artifacts |
| 8 | No Active P0 in gap matrix |
| 9 | Phase 09 readiness signed |
| 10 | Tracker rows **Frozen (runtime)** |

---

## Freeze sign-off

**P085-FINAL-FREEZE** entry in `PHASE085_CONSTITUTIONAL_CHANGELOG.md` after Step 36.

---

## Program closure vs Phase 09 start

| Milestone | Gate |
| --------- | ---- |
| CESP doctrine complete | Step 36 docs frozen |
| CESP runtime complete | G-P085-CLOSE-01 |
| Phase 09 authorized | G-P085-READY-01 + sign-off |
