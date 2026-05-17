# Phase 08 — Evaluation & quality governance

**Status:** normative.  
**Gates:** **G-P08-EVAL-01** (citation coverage), **G-P08-EVAL-02** (wording drift, non-blocking), **G-P08-TVER-01** (tenant slice).

---

## 1) Quality dimensions (non-semantic)

Phase **08** evaluation MUST NOT use “helpfulness” or open-ended LLM-judge as certification gates.

| Dimension | Metric | Gate |
| --------- | ------ | ---- |
| **Citation coverage** | `cited_claims / total_claims` | ≥ policy `min_citation_coverage` (default 0.95) |
| **Structural replay** | twin citation set match | G-P08-REPLAY-01 hard |
| **Omission completeness** | every omitted claim has SD-* | 100% |
| **Upstream fidelity** | no legality upgrade vs retrieval | 100% |
| **Schema validity** | artifact validates against JSON schema | 100% |
| **Caps respect** | no silent truncation | 100% |

---

## 2) Golden vectors

Corpus: `backend/tests/vector/domains/cortex/synthesis/synthesis_golden_vectors/v1/`

| Case id | Tests |
| ------- | ----- |
| `syn_causal_minimal_v1` | causal_chain → execution_understanding |
| `syn_degraded_tcre_gap_v1` | RD-TCRE-GAP → degradation_brief |
| `syn_empty_scope_v1` | SD-SCOPE-EMPTY lawful |
| `syn_replay_twin_v1` | structural twin pass |

Manifest: `corpus_manifest.json` with pinned retrieval fixtures reused from Phase **07** golden vectors where possible.

---

## 3) Evaluation harness

`run_synthesis_evaluation_suite_v1(session, tenant_id)`:

1. Run golden jobs in `prove` intent  
2. Compute metrics table  
3. Emit `evaluation_receipt` with pass/fail per gate  
4. Store in certification pack  

**surface_kind:** `verification_probe`

---

## 4) Drift controls

| Control | Action on drift |
| ------- | --------------- |
| Policy pack version bump | Re-run golden corpus in CI |
| Model route version bump | Block publish until policy pack updated |
| Prompt template change | New `prompt_template_version`; twin may fail until golden updated |
| Retrieval schema change | Coordinated Phase **07** + **08** bump |

---

## 5) Tenant verification slice (§Tenant)

`verify_tenant_synthesis_slice_v1` — included in tenant `/cortex/ingestion/verification` extension block `synthesis_substrate`:

| Check | Failure code |
| ----- | ------------ |
| Publication epoch exists | `no_synthesis_publication_epoch` |
| Default workload artifact exists | `no_default_artifact` |
| Last job < 24h or documented idle | `synthesis_stale` |
| SD-LLM-SCHEMA count = 0 (7d) | `llm_schema_failures` |
| G-P08-REPLAY-01 on sample | `replay_twin_failed` |

---

## 6) Readiness economics (Step 24)

Mirror Phase **05/06/07** economics receipt:

| Field | Meaning |
| ----- | ------- |
| `avg_job_duration_ms` | cost proxy |
| `avg_llm_tokens_per_artifact` | cost proxy |
| `artifacts_per_index_epoch` | throughput |
| `estimated_monthly_cost_band` | derived (catalog) |

**surface_kind:** `derived_aggregate` — not billing truth.

---

## 7) Human review (Phase 09 boundary)

Phase **08** MAY expose `operator_review_requested` flag on artifact — review UI lives in Phase **09**. Phase **08** only stores flag + timestamp.
