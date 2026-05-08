# Phase 02 Operator Decision Guidance Doctrine

## Purpose
Provide explicit operator actions for degraded trust states.

## Decision Matrix

| State | Operator Should Do | Operator Must Not Assume | Safe Actions | Unsafe Actions |
| ----- | ------------------ | ------------------------ | ------------ | -------------- |
| partial | inspect gap scope and verify if required workflows are affected | that absent evidence means absent event | scoped retrieval, scoped replay, verification rerun | broad trust claims |
| degraded | run continuity/provenance checks and isolate impacted windows | that replay outputs are publication-ready | scoped replay diagnostics, corruption scan | unbounded replay publish |
| unverifiable | restore verification evidence and rerun gates | any trust claim for affected scope | diagnostic reads, verification recovery | closure sign-off |
| replay-diverged | classify divergence class and block trusted output until resolved | that divergence is harmless | replay inspector analysis, scoped rerun | publish replay-derived outputs |
| continuity-broken | quarantine scope and perform lineage repair/recovery | that chronology/revision chains are intact | forensic inspection, recovery workflow | temporal reconstruction assertions |
| corrupted | trigger incident response and containment immediately | that evidence remains trustworthy | quarantine, validated recovery | normal replay/reconstruction |
| lineage-incomplete | fill lineage gaps or downgrade trust-state explicitly | audit completeness | provenance validation, scoped backfill where allowed | provenance-based guarantees |

## Global Rule
When in doubt, downgrade trust-state and preserve explicit uncertainty markers.
