# Phase 08 — Data contracts

**Status:** normative.  
**Schemas:** [`schemas/synthesis-job-envelope-v1.schema.json`](./schemas/synthesis-job-envelope-v1.schema.json), [`schemas/synthesis-intelligence-artifact-v1.schema.json`](./schemas/synthesis-intelligence-artifact-v1.schema.json).  
**Policy fixture:** [`fixtures/SynthesisPolicyPackV1_Default.json`](./fixtures/SynthesisPolicyPackV1_Default.json).

---

## §1 Synthesis workload classes (closed)

| `synthesis_workload_class` | Retrieval plan profile | Primary artifact_kind |
| -------------------------- | ---------------------- | --------------------- |
| `execution_understanding` | causal_chain + chronology_window | `execution_understanding` |
| `operational_synthesis` | degradation_survey + causal_chain | `operational_synthesis` |
| `execution_narrative` | causal_chain + traversal_lineage | `execution_narrative` |
| `management_intelligence` | operational_synthesis rollup | `management_intelligence` |
| `continuity_assessment` | ownership_continuity + execution_continuity | `continuity_assessment` |
| `degradation_brief` | degradation_survey | `degradation_brief` |
| `replay_equivalence_synthesis` | replay_equivalence (prove) | internal cert only |
| `pipeline_default` | policy-driven per index row | per tenant default |

---

## §2 Synthesis intent classes (closed)

| `synthesis_intent` | Meaning | LLM allowed? |
| ------------------ | ------- | ------------ |
| `inspect` | Operator understanding | Yes (bounded) |
| `prove` | Certification / twin | Yes (structural twin) |
| `audit` | Fail-closed on unverifiable upstream | Limited narration |
| `enumerate` | List claims only, minimal glue | Optional |
| `diff` | Compare two pinned artifact digests | Yes (diff claims only) |

---

## §3 SynthesisJobEnvelopeV1 (required fields)

| Field | Type | Rule |
| ----- | ---- | ---- |
| `schema_version` | `1` | const |
| `tenant_id` | uuid | required |
| `synthesis_workload_class` | enum | required |
| `synthesis_intent` | enum | required |
| `execution_partition` | `authoritative` \| `exploration` | required |
| `retrieval_scope` | object | addressing + optional pre-pinned lookup |
| `retrieval_pins` | object | MUST include `index_epoch`, `tcre_policy_bundle_digest` when causal |
| `synthesis_policy_pack_id` | string | default `SynthesisPolicyPackV1_Default` |
| `selection_policy` | object | caps: max_claims, max_retrieval_subqueries, max_llm_tokens |
| `idempotency_key` | string | recommended for pipeline |
| `substrate_pipeline_run_id` | uuid | set when pipeline-triggered |
| `pinned_retrieval_receipt` | object | optional; if set, verify replay identity |

**Forbidden:** see [`phase-08-anti-goals-doctrine.md`](./phase-08-anti-goals-doctrine.md).

---

## §Ingress — RetrievalEvidenceIngressV1

Phase **08** validates retrieval response before LLM:

| Check | Code |
| ----- | ---- |
| `retrieval_legality_class` ∈ allowed set for partition | `SYN-INGRESS-LEG-01` |
| `retrieval_query_replay_identity` non-empty | `SYN-INGRESS-REP-01` |
| `retrieval_evidence_hits` present (array) | `SYN-INGRESS-HIT-01` |
| No forbidden top-level keys from Phase **07** algebra | `SYN-INGRESS-ALG-01` |
| Exploration retrieval only if job exploration | `SYN-INGRESS-PAR-01` |
| Policy digest match | `SYN-INGRESS-POL-01` |

Stored on job row as `retrieval_ingress_digest`.

---

## §Citations — SynthesisCitationV1

See endgoal §8; citations are stable across replay when hit digests stable.

**Claim object:**

```json
{
  "claim_id": "clm-0001",
  "claim_kind": "temporal_fact | causal_link | ownership_fact | degradation_fact | discourse_only",
  "text": "…",
  "citations": ["cite-0001"],
  "omitted_reason": null,
  "discourse_only": false
}
```

---

## §Artifacts — SynthesisIntelligenceArtifactV1

| Section | Required |
| ------- | -------- |
| `schema_version` | yes |
| `artifact_id` | uuid |
| `artifact_kind` | enum |
| `artifact_digest` | sha256 canonical json |
| `synthesis_legality_class` | enum |
| `synthesis_job_replay_identity` | string |
| `retrieval_query_replay_identity` | string |
| `synthesis_policy_pack_digest` | string |
| `synthesis_publication_epoch` | string \| null (null until published) |
| `evidence_scope_summary` | object |
| `claims` | array (may be empty with SD-SCOPE-EMPTY) |
| `narrative_blocks` | optional array |
| `synthesis_citation_envelope` | object |
| `synthesis_omission_rows` | SD-* rows |
| `synthesis_degradation_rollup` | object |
| `synthesis_legality_posture` | object |
| `lineage_chain_digest` | string |
| `llm_trace_refs` | array |
| `retrieval_receipt_embed` | digest-pinned copy |
| `non_authoritative` | bool |

---

## §Persistence

### `cortex_synthesis_jobs`

| Column | Notes |
| ------ | ----- |
| `id` | uuid PK |
| `tenant_id` | FK |
| `status` | queued/running/completed/failed |
| `envelope_json` | full job envelope |
| `retrieval_ingress_digest` | after RETRIEVE |
| `synthesis_job_replay_identity` | after RECEIPT |
| `substrate_pipeline_run_id` | nullable |
| `celery_task_id` | nullable |

### `cortex_synthesis_artifacts`

| Column | Notes |
| ------ | ----- |
| `id` | uuid PK |
| `job_id` | FK |
| `artifact_digest` | unique per tenant |
| `body_json` | full artifact |
| `published` | bool |
| `synthesis_publication_epoch` | string when published |

### `cortex_synthesis_job_receipts`

Append-only: phase trace, timings, SD totals, twin flags.

### `cortex_synthesis_publication_epochs`

Per-tenant monotonic epoch string + `published_at` + `artifact_count`.

---

## §Receipt — synthesis_job_receipt

Mirrors retrieval receipt structure:

- `execution_trace[]` with phase timings
- `retrieval_subqueries[]` with replay identities
- `llm_invocations[]` with prompt hashes
- `receipt_digest`
- `synthesis_job_replay_identity`
