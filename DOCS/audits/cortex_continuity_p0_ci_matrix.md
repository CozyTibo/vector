# Cortex continuity P0 — CI proof script matrix

**Status:** CI / release gates only — **not** daily operator runbooks  
**Wave S5:** Operators use **two** scripts only — see [`cortex_semantic_ops_runbook.md`](cortex_semantic_ops_runbook.md)

| Operator truth | Script |
|----------------|--------|
| Runtime continuity | `backend/scripts/continuity_audit_snapshot.py` |
| Semantic / graph / retrieval / synthesis | `backend/scripts/graph_truth_audit_snapshot.py` |

---

## Proof scripts (pytest + optional prod receipt)

Each `continuity_p0_phase_*_proof.py` pairs with domain logic under `vector.domains.cortex.substrate_pipeline.continuity_p0_*`. Run in CI via targeted pytest modules; prod `--apply` flows require explicit operator approval.

| Script | Phase / step | Primary test module |
|--------|--------------|---------------------|
| `continuity_p0_phase0_closure.py` | P0 closure | `test_continuity_p0_phase0_closure.py` |
| `continuity_p0_phase0_signoff.py` | P0 signoff | (signoff harness) |
| `continuity_p0_phase05_proof.py` | Phase 05 | `test_continuity_p0_phase05_walks_persisted.py` |
| `continuity_p0_phase_a1_synthesis_job_reconcile_proof.py` | A1 | `test_continuity_p0_phase_a1_synthesis_job_reconcile.py` |
| `continuity_p0_phase_a2_ecs_deploy_align_proof.py` | A2 | `test_continuity_p0_phase_a2_ecs_deploy_align.py` |
| `continuity_p0_phase_a3_tcre_queued_drain_proof.py` | A3 | `test_continuity_p0_phase_a3_tcre_queued_drain.py` |
| `continuity_p0_phase_a4_aa_panel_strict_proof.py` | A4 | `test_continuity_p0_aa_panel_strict.py` |
| `continuity_p0_phase_a5_trace_only_ban_proof.py` | A5 | `test_continuity_p0_trace_only_policy.py` |
| `continuity_p0_phase_a6_synthesis_terminal_transitions_proof.py` | A6 | `test_continuity_p0_synthesis_terminal_transitions.py` |
| `continuity_p0_phase_b1_retrieval_publish_contract_proof.py` | B1 | `test_continuity_p0_retrieval_publish_contract.py` |
| `continuity_p0_phase_b2_retrieval_epoch_scope_alignment_proof.py` | B2 | `test_continuity_p0_retrieval_epoch_scope_alignment.py` |
| `continuity_p0_phase_b3_retrieval_registry_epoch_proof.py` | B3 | `test_continuity_p0_retrieval_registry_epoch.py` |
| `continuity_p0_phase_b4_phase05_walks_persisted_proof.py` | B4 | `test_continuity_p0_phase05_walks_persisted.py` |
| `continuity_p0_phase_b5_graph_hash_autonomous_chain_proof.py` | B5 | `test_continuity_p0_graph_hash_autonomous_chain.py` |
| `continuity_p0_phase_b6_post_ingestion_fresh_pipeline_run_proof.py` | B6 | `test_continuity_p0_post_ingestion_fresh_pipeline_run.py` |
| `continuity_p0_phase_c1_phase08_empty_scope_truth_proof.py` | C1 | `test_continuity_p0_phase08_empty_scope_truth.py` |
| `continuity_p0_phase_c2_synthesis_scope_caps_proof.py` | C2 | `test_continuity_p0_phase_c2_synthesis_scope_caps.py` |
| `continuity_p0_phase_c3_audit_snapshot_proof.py` | C3 | `test_continuity_p0_phase_c3_audit_snapshot.py` |
| `continuity_p0_phase_c4_aa_clock_restart_proof.py` | C4 | `test_continuity_p0_phase_c4_aa_clock_restart.py` |
| `continuity_p0_phase_c5_aa5_synthesis_jobs_completed_proof.py` | C5 | `test_continuity_p0_phase_c5_aa5_synthesis_jobs_completed.py` |
| `continuity_p0_phase_d1_admin_operator_primary_kpi_proof.py` | D1 | `test_continuity_p0_phase_d1_admin_operator_primary_kpi.py` |
| `continuity_p0_phase_d2_github_caps_align_proof.py` | D2 | `test_continuity_p0_phase_d2_github_caps_align.py` |
| `continuity_p0_phase_d3_graph_promotion_schedule_proof.py` | D3 | `test_continuity_p0_phase_d3_graph_promotion_schedule.py` |
| `continuity_p0_phase_d4_permanent_orphan_omission_proof.py` | D4 | `test_continuity_p0_phase_d4_permanent_orphan_omission.py` |
| `continuity_p0_phase_d5_legacy_coordinator_enqueue_deletion_proof.py` | D5 | `test_continuity_p0_phase_d5_legacy_coordinator_enqueue_deletion.py` |

**AA panel note:** `continuity_proof_panel.py` is a **continuity/runtime** surface. M3 / AA PASS is **not** semantic intelligence sign-off — use the Semantic readiness admin card or `graph_truth_audit_snapshot.py`.
