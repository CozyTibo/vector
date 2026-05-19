# Phase 08.5 — Testing strategy

**Status:** normative (Step 36 support).

---

## Gate wiring

| Gate | Test module (target) |
| ---- | -------------------- |
| G-P085-ANTI-IDLE-01 | `test_phase085_fake_green_completeness.py` |
| G-P085-CONT-01 | `test_phase085_pipeline_continuation.py` |
| G-P085-WATCH-01 | `test_phase085_stalled_recovery.py` |
| G-P085-RET-01 | `test_phase085_retrieval_materialization_report.py` |
| G-P085-SYN-02 | `test_phase085_synthesis_eligibility_classify.py` |
| G-P085-MAT-01 | `test_phase085_operational_maturity.py` |
| G-P085-HEALTH-01 | `test_phase085_operational_health_dimensions.py` |
| G-P085-HEALTH-02 | `test_phase085_autonomous_recovery_score.py` |
| G-P085-CP-01 | `test_phase085_operational_cockpit.py` |
| G-P085-CP-02 | `test_phase085_operational_explorers.py` |
| G-P085-CP-03 | `test_phase085_progression_timeline_causal.py` |
| G-P085-ECON-01 | `test_phase085_runtime_economics.py` |
| G-P085-ECON-02 | `test_phase085_replay_storm_handling.py` |
| G-P085-READY-01 | `test_phase085_phase09_readiness.py` |
| G-P085-CLOSE-01 | `test_phase085_cesp_cert_pack.py` |

---

## Scenario harness

**CESP-SCEN-A:** mock tenant ingest → post-ingestion → pipeline through TCRE (stub fast) → phase 07 → non-zero index.  
**CESP-SCEN-B:** stall injection (no TCRE callback) → watchdog recovers.  
**CESP-SCEN-C:** orphan graph → starvation flags → promotion pass → traversal.  
**CESP-SCEN-D:** eligible > 0 → synthesis jobs + activation audit.

---

## Soak

7-day cron on staging: collect `substrate_pipeline_07_08_completion_rate`, alert if < 95%.

---

## Admin e2e

Playwright: why-empty panel, stalled list, recover button, maturity dashboard.
