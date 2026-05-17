# Phase 08 — Endgoal doctrine (what “fully operational” means)

**Status:** normative.  
**Audience:** architects, operators, implementers, certification reviewers.

---

## 1) Executive endstate

A **fully operational Phase 08** means: for every tenant with a **published retrieval index epoch**, the substrate pipeline (or an operator-scoped manual job) can **automatically** produce **durable, replay-addressable synthesis intelligence artifacts** that explain **how execution moved** through the organization — grounded exclusively in Phase **07** evidence hits — without manual prompt crafting, without evidence fabrication, and without breaking replay law inherited from Phases **01–07**.

Phase 08 is the moment Vector becomes **execution intelligence** rather than **execution evidence substrate**.

---

## 2) Inputs (what enters Phase 08)

| Input class | Source | Required pins |
| ----------- | ------ | ------------- |
| **Retrieval query envelope** | Phase **07** `execute_retrieval_query_envelope_v1` | `retrieval_lookup_id`, `workload_class`, `intent`, `execution_partition`, `replay_pins` |
| **Retrieval response body** | Phase **07** authoritative output algebra | `retrieval_evidence_hits`, `retrieval_omission_rows`, `retrieval_query_receipt`, legality fields |
| **Retrieval replay identity** | Phase **07** | `retrieval_query_replay_identity` |
| **Published index epoch** | Phase **07** index materialization | `published_index_epoch`, row `index_epoch` |
| **Substrate pipeline receipt** | `substrate_pipeline` phase **07** completion | `pipeline_run_id`, `phase_run_id`, materialization digests |
| **Synthesis job envelope** | Phase **08** operator or pipeline | `synthesis_workload_class`, `synthesis_intent`, `synthesis_policy_pack_id` |
| **Optional scope anchors** | Addressing inheritance | `causal_chain_id`, `retrieval_walk_ref`, `org_entity_id`, `chronology_window_ref` |

**Forbidden ingress:** raw memory rows, canonical rows, graph edges, TCRE reducer internals, exploration-partition retrieval (unless `execution_partition=exploration` on synthesis job with explicit non-authoritative labeling).

---

## 3) Outputs (what leaves Phase 08)

| Output | Durability | Consumer |
| ------ | ---------- | -------- |
| **`SynthesisIntelligenceArtifactV1`** | Postgres + content-addressed digest | Phase **09** products, admin explorers, export APIs |
| **`synthesis_job_receipt`** | Append-only receipt row | Audit, replay twin, certification |
| **`synthesis_job_replay_identity`** | Receipt + artifact header | Double-run equivalence, drift detection |
| **`synthesis_legality_posture`** | Embedded in artifact | Operator gating, Phase **09** workflow guards |
| **`synthesis_citation_envelope`** | Per-claim pointers | Explainability UI, evaluation harness |
| **`synthesis_degradation_rollup`** | SD-* aggregation | Overview pipeline stage **synthesis** |
| **`synthesis_publication_epoch`** | Tenant-scoped monotonic string | Downstream “as-of intelligence” queries |

---

## 4) Intelligence artifacts (existence contract)

Each artifact MUST contain:

1. **Header** — tenant, workload, intent, partition, policy digest, replay identities (retrieval + synthesis), timestamps (processing, not “model guessed time”).
2. **Evidence scope summary** — deterministic rollup of hit counts, omission classes, upstream legality classes (**copied**, not re-inferred).
3. **Claims[]** — bounded list; each claim: `claim_id`, `claim_kind`, `text` (operator language), `citations[]`, `confidence_band` (structural only), `omitted_reason` when cite-or-omit applies.
4. **Narrative blocks** (optional per workload) — `execution_narrative`, `operational_synthesis`, `management_summary` — each subdivided into claims, never orphan prose.
5. **Continuity segment** — structural refs to identity/TCRE/OCTS bindings copied from retrieval hits.
6. **Lineage chain digest** — terminal artifact = synthesis artifact id; edges to retrieval receipt + index row.
7. **LLM trace refs** — pinned `model_route_id`, prompt template version, prompt hash, completion hash — **not** raw hidden chain-of-thought.

**Artifact kinds (closed enum, v1):**

| `artifact_kind` | Purpose |
| ----------------- | ------- |
| `execution_understanding` | What happened, in execution order, with gaps labeled |
| `operational_synthesis` | Cross-stream operational picture for operators |
| `execution_narrative` | Time-bounded story with explicit uncertainty frontiers |
| `management_intelligence` | Aggregated posture suitable for leadership (still cite-bound) |
| `continuity_assessment` | Ownership/execution continuity interpretation |
| `degradation_brief` | SD-* and RD-* propagated explanation |

---

## 5) Deterministic vs probabilistic split

| Concern | Deterministic (MUST) | Probabilistic (MAY, bounded) |
| ------- | -------------------- | ------------------------------ |
| Job validation, caps, legality aggregation | Yes | No |
| Retrieval fan-out plan (which queries) | Yes | No |
| Evidence hashing, citation keys | Yes | No |
| Replay identity, receipt digest | Yes | No |
| Claim slot planning (sections, max claims) | Yes | No |
| Natural language phrasing inside claim slots | No | Yes (LLM) |
| Wording of narrative glue between claims | No | Yes (LLM) |
| Ordering of claims within a section | Yes (policy profile) | No |
| Introducing new facts not in hits | **Forbidden** | **Forbidden** |

**Rule SYN-END-01:** Probabilistic components MAY only **verbalize** evidence already present in the citation envelope. They MUST NOT introduce entities, timestamps, causality, or ownership not supported by citations.

---

## 6) What the LLM is allowed to do

| Allowed | Forbidden |
| ------- | --------- |
| Rephrase cited facts into operator language | Invent events, people, systems, dates |
| Connect claims with discourse glue explicitly marked `discourse_only: true` | Present discourse as evidentiary |
| Summarize **within** a capped hit set already retrieved | Trigger new retrieval or “search more” |
| Emit structured JSON matching `SynthesisIntelligenceArtifactV1` | Emit markdown essays without claim structure |
| Refuse / shorten when caps exceeded | Silently drop omissions |
| Use policy-pack phrasing templates | Override legality or replay pins |

**Model routing:** Only routes registered in `SynthesisPolicyPackV1` with `authority_class ∈ {narration, structuring}` — never `{substrate_truth, legality_override}`.

---

## 7) What remains hard deterministic

- Ingress validation (**G-P08-INGRESS-***)
- Retrieval sub-query plan execution order
- Cite-or-omit enforcement per claim
- SD-* omission emission
- Synthesis legality class aggregation
- `synthesis_job_replay_identity` computation
- Publication epoch bump preconditions
- Pipeline phase **08** completion predicate
- Anti-goal static scans (forbidden keys in envelopes/artifacts)

---

## 8) Evidence citation model

Each citation MUST include:

```json
{
  "citation_id": "cite-…",
  "retrieval_lookup_id": "…",
  "hit_index": 0,
  "hit_digest": "sha256:…",
  "evidence_legality_class": "verified",
  "retrieval_omission_classes": [],
  "source_artifact_kind": "tcre_chain",
  "source_artifact_ref": "chain-…",
  "quoted_fields": ["provenance.upstream_digest", "temporal_scope.t_as_of_unix_ns"]
}
```

**Cite-or-omit (SYN-LAW-09):** If a claim cannot cite ≥1 hit field, the claim MUST be omitted and `SD-CITE-GAP` recorded — never “best effort” citation.

---

## 9) Replay-safe synthesis

Authoritative synthesis is replay-safe when:

1. Same `SynthesisJobEnvelopeV1` + same `SynthesisPolicyPackV1` digest + same retrieval `retrieval_query_replay_identity` ⇒ same `synthesis_job_replay_identity`.
2. Twin LLM runs with pinned temperature=0 and pinned prompt hash ⇒ **structural equivalence** of claims (claim kinds + citation sets); wording MAY differ only in `discourse_only` fields flagged for evaluation, not for certification.
3. Certification path requires **structural twin pass** (G-P08-REPLAY-01); wording drift tracked separately (G-P08-EVAL-02).

---

## 10) Explainability contract

Operators MUST answer without SQL:

| Question | Where answered |
| -------- | -------------- |
| Why this claim? | Citation explorer → hit provenance |
| Why missing? | SD-* omission explorer |
| Why degraded? | Degradation rollup + upstream RD-* |
| What retrieval backed this? | Frozen retrieval receipt embed |
| Can I replay it? | Replay explorer → twin diff |
| What model phrased it? | LLM trace refs (pinned) |

---

## 11) Integration with future operational products (Phase 09)

Phase **09** workflows orchestrate **calls** to synthesis artifacts — they do not re-run LLM. Phase **08** artifacts expose:

- `artifact_ref` for workflow pinning
- `synthesis_publication_epoch` for “latest intelligence as-of”
- `workflow_binding_hints` (non-authoritative catalog) suggesting which Phase **09** templates apply

---

## 12) Operational completion checklist (tenant-level)

Phase **08** is **operationally complete** for tenant `T` when ALL hold:

- [ ] Substrate pipeline runs **phase_08_synthesis** automatically after **phase_07_retrieval** publish
- [ ] ≥1 authoritative artifact per default workload in policy pack (or documented SD-SCOPE-EMPTY)
- [ ] `synthesis_publication_epoch` monotonic and visible on overview
- [ ] Admin control plane surfaces (runtime_backed) show job lag < policy SLO
- [ ] Tenant verification slice **G-P08-TVER-01** passes
- [ ] **SYNTHESIS-CERT-PACK-1** archived for tenant cohort
- [ ] No **Active P0** in [`synthesis-spec-gap-matrix.md`](./synthesis-spec-gap-matrix.md)

---

## 13) Non-goals (explicit)

Phase **08** endstate does **not** include: autonomous agents, embedding search, conversational memory, cross-tenant learning, automatic remediation actions, or Phase **09** UX. Those are downstream or forbidden.
