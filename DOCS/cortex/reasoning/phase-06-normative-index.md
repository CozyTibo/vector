# Phase 06 — Normative index (temporal–causal execution reconstruction)

**Status:** normative specification program — **PHASE06_PROGRAM_FREEZE_VERSION `1`** (see §Program freeze).  
**Role:** single constitutional entry for TCRE (temporal–causal **execution reconstruction**); step↔doctrine map (**Steps 1–35**); shared vocabulary; **FF‑P06‑0..5** freeze-bundle registry; dependency gate on OCTS **19–23**.  
**Non‑negotiable:** This is **not** an AI reasoning engine, semantic cognition layer, or probabilistic org model.  
**Non‑role:** This index SHALL NOT substitute for step-specific doctrines; each linked file is independently normative for its slice.

**Normative tree:** this directory (`DOCS/cortex/reasoning/`).  
**Changelog (pre‑implementation hardening):** [`PHASE06_CONSTITUTIONAL_CHANGELOG.md`](./PHASE06_CONSTITUTIONAL_CHANGELOG.md).  
**Implementation contract:** [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md).  
**Canonical default policy:** [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md) + [`fixtures/ReasoningPolicyPackV1_Default.json`](./fixtures/ReasoningPolicyPackV1_Default.json).  
**Live runtime (bounded, not production-certified):** [`PHASE06_RUNTIME02_OPERATOR_VISIBILITY.md`](./PHASE06_RUNTIME02_OPERATOR_VISIBILITY.md); `vector.domains.cortex.reasoning.runtime` (**RUNTIME-01** reconstruction + **RUNTIME-02** operator projections).  
**Code anchors (P06-01 … P06-35):** `vector.domains.cortex.reasoning.normative.PHASE06_PROGRAM_FREEZE_VERSION`; `vector.domains.cortex.reasoning.anti_goals` (**G‑P06‑ANTI‑01**, JSON cognition guards); `vector.domains.cortex.reasoning.execution_causality_constraints` (**P06‑03**, **P06‑20** — **`CAUSAL_LEGALITY_ENUM_VERSION_V1`**, **`verify_gp06_clc01`..`clc04`**, **`TCRECausalEdge_v1`** stub + **L‑REL** key guard); `vector.domains.cortex.reasoning.organizational_continuity_reasoning` (Phase **04** continuity gates + **`replay_conflicted`** handoff); `vector.domains.cortex.reasoning.temporal_reasoning` (T‑TEMP‑*, half-open ISO, **`replay_safe_ordering`** literals); `vector.domains.cortex.reasoning.chronology_legality` (**P06‑06** — **`ChronologyLegalityProjectionV1`**, **CHRON‑FORB‑1**, default **`chronology_skew_projection_v1`** + digest **`TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST`**); `vector.domains.cortex.reasoning.temporal_anchor_resolution` (**P06‑07** — **`temporal_anchor_resolution_order_v1`**, **`reasoning_temporal_anchor_resolution_receipt`**, **`declare_replay_safe_ordering_v1`**); `vector.domains.cortex.reasoning.interval_continuity` (**P06‑08** — half-open interval chain closure, read-only **`replay_safe_ordering`**, **`reasoning_chronology_receipt`**); `vector.domains.cortex.reasoning.replay_chronology` (**P06‑09** — pinned replay tuple A–E, **`reasoning_replay_permutation_v1`**, tuple bridge to chronology snapshot, **`reasoning_replay_receipt`** sketch); `vector.domains.cortex.reasoning.replay_safe_reasoning_posture` (**P06‑21** — **`validate_replay_safe_reasoning_posture_v1`**, **`verify_gp06_rsp01`..`rsp04`**, **`tcre_policy_bundle_digest`** shape on pinned (C)); `vector.domains.cortex.reasoning.temporal_conflict_resolution` (**P06‑10** — **`temporal_conflict_precedence_rank_v1`**, **`TEMPORAL_CONFLICT_CLASS_IDS`**, non-rewrite + **`chronology_projection_snapshot_from_temporal_conflict_v1`**); `vector.domains.cortex.reasoning.chronology_degradation_propagation` (**P06‑11** — **`CD‑CHRON`** from chronology band, **`normalize_degradation_corpus_token_v1`**, **DEG‑MON‑1** display sort, **`validate_policy_caps_g_p06_pol01_v1`**, **`effective_max_causal_hops_v1`**); `vector.domains.cortex.reasoning.causal_ambiguity_propagation` (**P06‑22** — **`TCRE_AMBIGUITY_REGISTRY_VERSION`**, **`normalize_ambiguity_corpus_token_to_registry_id_v1`**, **`verify_gp06_amb01`..`amb05`**, **AMB‑S1**); `vector.domains.cortex.reasoning.unverifiable_degraded_causality` (**P06‑23** — **`CAUSAL_LEGALITY_UNVERIFIABLE_V1`**, **`validate_unverifiable_causality_requires_cd_codes_v1`**, **`validate_cd_multiset_monotonic_extension_degraded_v1`**, **`verify_gp06_udc01`..`udc05`**); `vector.domains.cortex.reasoning.reasoning_provenance_law` (**P06‑24** — **`validate_reasoning_artifact_provenance_envelope_v1`**, **`REASONING_REPLAY_POSTURE_LITERALS_V1`**, **`verify_gp06_rpl01`..`rpl05`**); `vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts` (**P06‑25** — **`REASONING_RECEIPT_TYPES_V1`**, **`hash_reasoning_canonical_json_sha256_v1`**, **`verify_gp06_rra01`..`rra05`**); `vector.domains.cortex.reasoning.replay_equivalence_proofs` (**P06‑26** — **`GP06_REPLAY_01_GATE_ID_V1`**, **`normalize_gp06_replay_01_comparison_vector_v1`**, **`compare_gp06_replay_01_double_run_v1`**, **`verify_gp06_req01`..`req06`**); `vector.domains.cortex.reasoning.causal_drift_proofs` (**P06‑27** — **`hash_breakpoint_id_v1`**, **`sort_breakpoint_index_rows_v1`**, **`validate_drift_degradation_receipt_links_breakpoints_v1`**, **`verify_gp06_cdp01`..`cdp05`**); `vector.domains.cortex.reasoning.proof_bundle_composition` (**P06‑28** — **`build_proof_bundle_inner_digest_body_v1`**, **`hash_proof_bundle_inner_digest_v1`**, **`validate_proof_bundle_equivalence_receipt_set_v1`**, **`verify_gp06_pbc01`..`pbc05`**); `vector.domains.cortex.reasoning.reasoning_verification_harness` (**P06‑29** — **`REASONING_GP06_DOCTRINE_GATE_IDS_V1`**, **`run_reasoning_gp06_wired_verification_stages_v1`**, **`verify_gp06_rvh01`..`rvh03`**); `vector.domains.cortex.reasoning.reasoning_ci_enforcement_architecture` (**P06‑31** — **`reasoning_gp06_ci_full_stage_row_map_v1`**, **`REASONING_GP06_CI_PR_BLOCKING_STAGES_V1`**, **`verify_gp06_cia01`..`cia08`**, **`run_reasoning_gp06_ci_pr_blocking_bundle_v1`**); `vector.domains.cortex.reasoning.reasoning_control_plane` (**P06‑32** — **`REASONING_CONTROL_PLANE_SURFACES_V1`**, **`build_reasoning_control_plane_catalog_v1`**, **`verify_gp06_rcp01`..`rcp06`**); `vector.domains.cortex.reasoning.reasoning_runtime_legality_matrix` (**P06‑33** — **`REASONING_RUNTIME_LEGALITY_PREDICATES_V1`**, **`build_reasoning_runtime_legality_matrix_catalog_v1`**, **`verify_gp06_rlm01`..`rlm07`**); `vector.domains.cortex.reasoning.reasoning_tenant_verification_slice` (**P06‑34** — **`build_org_graph_reasoning_verification_slice_v1`**, **`verify_gp06_rtvs01_org_graph_reasoning_slice_golden_static`**, **`verify_gp06_rtvs02_admin_openapi_path_matrix_static`**); `vector.domains.cortex.reasoning.reasoning_readiness_economics` (**P06‑34** — **`build_reasoning_readiness_economics_receipt_v1`**, **`verify_gp06_rreco01_readiness_economics_clean_profile_static`**, **`verify_gp06_rreco02_readiness_economics_hostile_profile_static`**, **`verify_gp06_rreco03_admin_openapi_path_matrix_static`**); `vector.domains.cortex.reasoning.reasoning_certification_pack` (**P06‑35** — **`TCRE-CERT-PACK-1`**, **`build_reasoning_certification_pack_snapshot_v1`**, **`verify_gp06_close01_tcre_cert_pack_closure_static`**, **`verify_gp06_rcpk01_reasoning_cert_pack_admin_openapi_path_matrix_static`**); `vector.domains.cortex.reasoning.reasoning_golden_thread_binding` (**P06‑30** — **`reasoning_golden_vectors_v1_root`**, **`bind_reasoning_golden_corpus_at_root_v1`**, **`verify_gp06_gtc01`..`gtc05`**); `vector.domains.cortex.reasoning.cross_system_time_reconciliation` (**P06‑12** — **`continuity_bridge_strength_rank_v1`**, **`cross_system_causal_effective_min_rank_v1`**, **CROSS‑CAUS‑1/2**, **`skew_flag_tuple_from_reasoning_snapshot_v1`**, **`validate_chronology_allows_strict_temporal_order_claim_v1`**); `vector.domains.cortex.reasoning.causal_interval_closure` (**P06‑13** — **`validate_causal_influence_half_open_chain_v1`**, **`canonical_sorted_tcre_causal_edge_ids_v1`**, hop + breakpoint caps); `vector.domains.cortex.reasoning.causal_reconstruction_substrate` (**P06‑14** — **`COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1`**, **`validate_tcre_causal_edge_v1_reconstruction_substrate`**, **`validate_cross_system_tcre_support_not_weak_only_v1`**, **`TCRE_CAUSAL_EDGE_REGISTRY_VERSION`**); `vector.domains.cortex.reasoning.deterministic_causal_chain` (**P06‑15** — **`hash_causal_chain_id_v1`**, **`causal_chain_id_canonical_body_v1`**, **`verify_causal_chain_id_v1`**, **`validate_tcre_policy_bundle_digest_shape_v1`**); `vector.domains.cortex.reasoning.causal_propagation_policy` (**P06‑16** — **`merge_rules_coordination_edges`**, **`max_underlying_coordination_edges_for_tcre_kind_v1`**, **`validate_tcre_edge_v1_stub_with_propagation_policy_v1`**, optional **`propagation_rule_table_v1`**); `vector.domains.cortex.reasoning.causal_graph_ownership_continuity` (**P06‑17** — **`validate_tcre_causal_graph_ownership_continuity_v1`**, **`validate_tcre_causal_edge_v1_reconstruction_substrate_with_ownership_v1`**, **`tcre_edge_cites_concrete_coordination_edge_ids_v1`**); `vector.domains.cortex.reasoning.commitment_derived_causality` (**P06‑18** — **`validate_tcre_commitment_transition_causality_v1`**, **`validate_tcre_causal_edge_v1_reconstruction_substrate_commitment_transition_v1`**, **`TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1`**, §4.2 sentinel lineage); `vector.domains.cortex.reasoning.negative_signal_causality` (**P06‑19** — **`validate_tcre_negative_signal_causality_v1`**, **`validate_tcre_causal_edge_v1_reconstruction_substrate_negative_signal_v1`**, **`TCRE_NEGATIVE_SIGNAL_DERIVATION_RULE_PREFIX_V1`**, **`NEGATIVE_SIGNAL_KINDS_SILENCE_CAUSALITY_LAWFUL_V1`**, §4.2 sentinel lineage + **`silence-causality-law.md`** §1); substrate contracts `vector.domains.cortex.ingestion.execution_reconstruction_contracts`; Phase **05** OCTS (`vector.domains.cortex.traversal`); Phase **04** org graph projection ingress; Phases **01–03** raw → canonical pipeline.

**Upstream (hard):** Phase **05** OCTS walk/replay/tenant verification (Steps **19–23** minimum); Phase **04** continuity + projection export; Phase **03** canonical materializations; Phase **02** raw memory trust gates.  
**Downstream:** Retrieval/synthesis phases MUST consume TCRE only through contracts in this tree.

---

## Program freeze (P06-01)

| Field | Value |
| ----- | ----- |
| **PHASE06_PROGRAM_FREEZE_VERSION** | `1` — MUST match runtime constant `vector.domains.cortex.reasoning.normative.PHASE06_PROGRAM_FREEZE_VERSION` (shipped **P06-01**). |
| **Scope** | Normative index; vocabulary; document hierarchy; **FF‑P06‑0..5**; step program **1–35**; alignment with [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md) freeze discipline. |
| **Constitutional boundary** | TCRE is **deterministic temporal ordering + evidence-bounded causal chains** only — see [`phase-06-anti-goals-doctrine.md`](./phase-06-anti-goals-doctrine.md). |

**REPLAY REQUIREMENT:** Any TCRE artifact labeled **authoritative** MUST reproduce under pinned inputs per [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) and [`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md), including active **`tcre_policy_bundle_digest`**.

---

## Freeze bundle registry (FF‑P06‑0..5)

Bundles are **doctrine freeze checkpoints**; **FF‑P06‑5** aligns with phase closure (**G‑P06‑CLOSE‑01**). Runtime MUST NOT ship a Phase **06** persistence surface until prior bundles for its slice are satisfied (see step table).

| Bundle | Steps (tracker §3) | Intent |
|--------|---------------------|--------|
| **FF‑P06‑0** | 1–2 | Index + anti‑goals |
| **FF‑P06‑1** | 1–8 | Temporal substrate law |
| **FF‑P06‑2** | 1–12 | Temporal + chronology legality + **state machine** |
| **FF‑P06‑3** | 1–20 | + Causal substrate (**TCRE edge registry**) + §4 causal legality class |
| **FF‑P06‑4** | 1–26 | + Legality + proof receipts + **policy pack** |
| **FF‑P06‑5** | 1–35 | + Verification harness + control plane + runtime legality + closure |

**Dependency gate:** No Phase **06** **runtime package** until Phase **05** **Steps 19–23** minimum (walk replay / tenant slice / citeable structural evidence) **and** Phase **06** doctrine is **`Frozen (doctrine)`** for the **Steps 1–35** program (`P06-FINAL-FREEZE-2026-05-13`; see [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md) + [`PHASE06_CONSTITUTIONAL_CHANGELOG.md`](./PHASE06_CONSTITUTIONAL_CHANGELOG.md)).

---

## Step program ↔ primary doctrine (1:1)

| Step | Title | Primary normative file(s) |
| ---- | ----- | ------------------------- |
| 1 | Normative index + program freeze | **This file** |
| 2 | Anti‑goals + forbidden cognition | [`phase-06-anti-goals-doctrine.md`](./phase-06-anti-goals-doctrine.md) |
| 3 | Observed vs derived boundary | [`execution-causality-constraints.md`](./execution-causality-constraints.md) |
| 4 | Upstream continuity law | [`organizational-continuity-reasoning.md`](./organizational-continuity-reasoning.md) |
| 5 | Temporal reasoning substrate | [`temporal-reasoning-doctrine.md`](./temporal-reasoning-doctrine.md) |
| 6 | Chronology legality | [`chronology-legality-law.md`](./chronology-legality-law.md); [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md); [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |
| 7 | Temporal anchor resolution | [`temporal-anchor-resolution-spec.md`](./temporal-anchor-resolution-spec.md) |
| 8 | Interval continuity + half‑open closure | [`temporal-reasoning-doctrine.md`](./temporal-reasoning-doctrine.md); [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) |
| 9 | Replay chronology semantics | [`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md); [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md); [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) |
| 10 | Late‑arrival + skew legality | [`temporal-conflict-resolution-law.md`](./temporal-conflict-resolution-law.md) |
| 11 | Chronology degradation propagation | [`causal-degradation-spec.md`](./causal-degradation-spec.md); [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |
| 12 | Cross‑system time reconciliation | [`cross-system-causal-continuity.md`](./cross-system-causal-continuity.md); [`chronology-legality-law.md`](./chronology-legality-law.md) |
| 13 | Causal interval closure | [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md); [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |
| 14 | Causal reconstruction substrate | [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md); [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) |
| 15 | Deterministic causal chains | [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md); [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md); [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |
| 16 | Escalation / dependency / blocker propagation | [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md); [`execution-causality-constraints.md`](./execution-causality-constraints.md); [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |
| 17 | Ownership continuity in causal graphs | [`organizational-continuity-reasoning.md`](./organizational-continuity-reasoning.md); [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) |
| 18 | Commitment‑derived causality | [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md); [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) |
| 19 | Negative‑signal causality | [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md); [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md); [`silence-causality-law.md`](./silence-causality-law.md) |
| 20 | Causal legality classes | [`execution-causality-constraints.md`](./execution-causality-constraints.md) §4 |
| 21 | Replay‑safe reasoning posture | [`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md); [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) |
| 22 | Ambiguity propagation (causal) | [`bounded-ambiguity-law.md`](./bounded-ambiguity-law.md); [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md) |
| 23 | Unverifiable / degraded causality | [`causal-degradation-spec.md`](./causal-degradation-spec.md) |
| 24 | Reasoning provenance law | [`reasoning-provenance-law.md`](./reasoning-provenance-law.md) |
| 25 | Reasoning receipts + artifacts | [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md) |
| 26 | Temporal / causal replay proofs | [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md); [`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md) |
| 27 | Causal drift proofs | [`causal-degradation-spec.md`](./causal-degradation-spec.md); [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md) |
| 28 | Proof bundle composition | [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md); [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md) §2 |
| 29 | **G‑P06‑*** verification harness | [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md) |
| 30 | Golden corpus binding | [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md); [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md); [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md); [`causal-degradation-spec.md`](./causal-degradation-spec.md) |
| 31 | CI enforcement architecture (Phase 06) | [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md) §Staging |
| 32 | **Reasoning Control Plane** (admin) | [`reasoning-admin-control-plane-spec.md`](./reasoning-admin-control-plane-spec.md) |
| 33 | Runtime legality matrix | [`reasoning-runtime-legality-matrix.md`](./reasoning-runtime-legality-matrix.md) |
| 34 | Tenant verification slice + readiness economics | [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md); [`reasoning-admin-control-plane-spec.md`](./reasoning-admin-control-plane-spec.md) |
| 35 | Closure + certification (**G‑P06‑CLOSE‑01**) | [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md) §Gate catalog |
| — | *Shared* | [`reasoning-idempotency-and-retry-doctrine.md`](./reasoning-idempotency-and-retry-doctrine.md) |

**Doctrine freeze (`P06-FINAL-FREEZE-2026-05-13`):** Program-level **`Frozen (doctrine)`** for Steps **1–30** is authoritative in [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md).

---

## Registry / machine owners (single source)

| Concern | Owner doc |
|---------|-----------|
| **`tcre_causal_edge_kind`** + coordination mapping | [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md) |
| **`ambiguity_class_id` (`AMB‑*`)** | [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md) |
| **Policy caps + digests** | [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md) · canonical default [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md) |
| **Chronology / replay tuple law** | [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) |
| **Silence → causal** | [`silence-causality-law.md`](./silence-causality-law.md) |
| **Gaps / freeze discipline** | [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md) |

---

## Doctrine reading order (first implementation wave)

1. [`PHASE06_IMPLEMENTATION_HANDOFF.md`](./PHASE06_IMPLEMENTATION_HANDOFF.md)  
2. [`phase-06-anti-goals-doctrine.md`](./phase-06-anti-goals-doctrine.md)  
3. [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md)  
4. [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md)  
5. [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md)  
6. [`reasoning-policy-pack-v1-default.md`](./reasoning-policy-pack-v1-default.md)  
7. [`reasoning-provenance-law.md`](./reasoning-provenance-law.md)  
8. [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md)  
9. [`bounded-ambiguity-law.md`](./bounded-ambiguity-law.md)  
10. [`chronology-legality-law.md`](./chronology-legality-law.md)  
11. [`temporal-reasoning-doctrine.md`](./temporal-reasoning-doctrine.md)  
12. [`silence-causality-law.md`](./silence-causality-law.md)  
13. [`causal-reconstruction-doctrine.md`](./causal-reconstruction-doctrine.md)  
14. [`deterministic-causal-chain-spec.md`](./deterministic-causal-chain-spec.md)  
15. [`causal-breakpoint-detection-spec.md`](./causal-breakpoint-detection-spec.md)  
16. [`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md)  
17. [`replay-aware-reasoning-law.md`](./replay-aware-reasoning-law.md)  
18. [`replay-equivalence-reasoning-spec.md`](./replay-equivalence-reasoning-spec.md)  
19. [`reasoning-runtime-legality-matrix.md`](./reasoning-runtime-legality-matrix.md)  
20. [`reasoning-admin-control-plane-spec.md`](./reasoning-admin-control-plane-spec.md)  
21. [`reasoning-verification-harness-spec.md`](./reasoning-verification-harness-spec.md)

---

## Vocabulary (stable — MUST NOT overload)

| Term | Definition |
| ---- | ---------- |
| **TCRE** | **Temporal & causal execution reconstruction** — deterministic temporal ordering and evidence-bounded causal chains over replay-safe organizational exhaust and OCTS receipts; not LLM reasoning. |
| **TemporalAnchorChain** | Substrate contract object carrying **`replay_safe_ordering`** ∈ {`strict`, `partial`, `unresolved`} per `execution_reconstruction_contracts`; Phase **06** treats it as **read-only** for legality projection. |
| **ChronologyLegalityProjectionV1** | Deterministic policy lookup (**§2.1** of [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md)) mapping snapshot flags + **`replay_safe_ordering`** → **`chronology_legality_class`**. |
| **CHRON‑FORB‑1** | Closure law forbidding selected **`(replay_safe_ordering, chronology_legality_class)`** pairs without a matching exception row / partitioned override. |
| **TCRECausalEdge_v1** | Derived causal edge artifact; kind ∈ closed **`tcre_causal_edge_kind`** per [`tcre-causal-edge-registry-v1.md`](./tcre-causal-edge-registry-v1.md), distinct from coordination ledger edges. |
| **tcre_policy_bundle_digest** | `sha256` over canonical policy JSON (excluding digest field); **MUST** participate in edge ids, chain ids, and replay equivalence inputs per [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md). |

**Cross‑links:** [`../continuity/conflict-resolution-doctrine.md`](../continuity/conflict-resolution-doctrine.md); [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md); [`../05-traversal/phase-05-normative-index.md`](../05-traversal/phase-05-normative-index.md); [`reasoning-spec-gap-matrix.md`](./reasoning-spec-gap-matrix.md); [`reasoning-idempotency-and-retry-doctrine.md`](./reasoning-idempotency-and-retry-doctrine.md); [`execution-state-transition-law.md`](./execution-state-transition-law.md).
