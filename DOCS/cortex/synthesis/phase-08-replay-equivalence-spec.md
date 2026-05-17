# Phase 08 — Replay & equivalence model

**Status:** normative.  
**Gate:** **G-P08-REPLAY-01** (structural twin), **G-P08-REPLAY-02** (publication epoch monotonicity).

---

## 1) synthesis_job_replay_identity

Computed after `RECEIPT` from canonical JSON:

```text
synthesis_job_replay_identity = sha256_v1({
  synthesis_policy_pack_digest,
  synthesis_workload_class,
  synthesis_intent,
  execution_partition,
  retrieval_query_replay_identity,        # primary sub-query
  retrieval_subquery_replay_identities[], # sorted
  retrieval_ingress_digest,
  claim_slot_plan_digest,
  prompt_hashes[],                         # sorted
  model_route_ids[],                       # sorted
  synthesis_orchestrator_build_id,
})
```

**Rule SYN-REP-01:** MUST NOT include LLM completion text — only pins.

---

## 2) Retrieval replay coupling

| Rule | Text |
| ---- | ---- |
| **SYN-REP-02** | If retrieval twin diverges, synthesis MUST NOT claim `synthesis_replay_safe`. |
| **SYN-REP-03** | Stored `retrieval_receipt_embed` MUST verify against live re-query when operator triggers “verify replay”. |
| **SYN-REP-04** | Pipeline jobs MUST pin `published_index_epoch` from phase **07** receipt. |

---

## 3) LLM twin semantics (§Twin)

### Structural equivalence (certification path)

Two LLM invocations with identical pins MUST produce artifacts where:

- `claims[].claim_kind` sequences match
- `claims[].citations` sets match (citation_id → hit_digest)
- `synthesis_omission_rows` SD-* multisets match
- `discourse_only` text MAY differ (flagged in twin diff)

### Wording equivalence (evaluation only)

**G-P08-EVAL-02** — BLEU/semantic similarity optional; **never** blocks closure.

### Twin execution modes

| Mode | When |
| ---- | ---- |
| `inline_twin` | `synthesis_intent=prove` |
| `harness_twin` | CI golden vectors |
| `operator_twin` | Admin replay explorer |

---

## 4) Artifact digest equivalence

`artifact_digest = sha256(canonical_json(artifact_body_without_discourse_only_text))`

Certification compares structural digest; stores wording diff separately.

---

## 5) Publication replay

**G-P08-REPLAY-02:** `synthesis_publication_epoch` MUST only advance when:

1. Artifact `synthesis_legality_class` ∈ {`synthesis_replay_safe`, `synthesis_degraded`}
2. `synthesis_job_replay_identity` matches prior published artifact for same scope OR first publish
3. `published_index_epoch` on retrieval pins ≤ current published index epoch

Rollback forbidden — forward-only epochs (operator “retract” marks artifact `retracted` without deleting history).

---

## 6) Drift detection

| Drift kind | Detection |
| ---------- | --------- |
| Policy pack drift | digest mismatch on re-run |
| Retrieval drift | retrieval replay identity mismatch |
| Model route drift | model version bump without policy bump |
| Prompt template drift | template version change |

All emit `SD-REPLAY-DRIFT` in degradation explorer.
