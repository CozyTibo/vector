# Reasoning provenance law (Phase 06)

**Status:** constitutional law.  
**Applies to:** every temporal or causal artifact emitted by Phase **06** reducers.

---

## 1. Required fields (conceptual)

Each artifact MUST carry:

| Field | Role |
|-------|------|
| **Provenance** | `EvidenceLineageHop[]` + `source_raw_record_ids` minimums per parent contracts. |
| **Legality** | `replay_posture` + `chronology_legality_class` + `causal_legality_class` — enums frozen in [`chronology-replay-legality-state-machine.md`](./chronology-replay-legality-state-machine.md) and [`execution-causality-constraints.md`](./execution-causality-constraints.md). |
| **Confidence source** | `DeterministicConfidenceSource` only — no floats. |
| **Ambiguity class** | `ambiguity_class_id` from [`ambiguity-registry-v1.md`](./ambiguity-registry-v1.md); `AMB‑NONE` explicit. |
| **Continuity lineage** | References to org continuity bridges when cross‑system (Phase **04**). |
| **Replay posture** | `replay_equivalent` \| `replay_degraded` \| `replay_partial` \| `replay_unverifiable` \| `replay_conflicted` — align [`../verification/golden-thread-replay-corpus-spec.md`](../verification/golden-thread-replay-corpus-spec.md) §5. |
| **Degradation semantics** | Sorted list of **`CD‑*`** codes per [`causal-degradation-spec.md`](./causal-degradation-spec.md); optional coarse tag **`degradation_coarse`** ∈ {`none`, `composite`} where **`composite`** means `len(CD_codes)>1`. **Deprecated:** vague `chronology` \| `causal` \| `continuity` single‑word tags without `CD‑*`. |

---

## 2. Survivability

Artifacts **survive** downgrade: provenance is never stripped to “fix” UI — only additional degradation receipts append.

---

## 3. Related

[`reasoning-receipts-and-proof-artifacts.md`](./reasoning-receipts-and-proof-artifacts.md) · [`reasoning-policy-pack-v1.md`](./reasoning-policy-pack-v1.md)
