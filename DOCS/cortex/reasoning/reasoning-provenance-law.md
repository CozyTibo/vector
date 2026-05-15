# Reasoning provenance law (Phase 06)

**Status:** constitutional law.  
**Applies to:** every temporal or causal artifact emitted by Phase **06** reducers.

## Required fields (conceptual)

Each artifact MUST carry:

| Field | Role |
|-------|------|
| **Provenance** | `EvidenceLineageHop[]` + `source_raw_record_ids` minimums per parent contracts. |
| **Legality** | `replay_posture` + `chronology_legality_class` + `causal_legality_class` (enums frozen in harness spec). |
| **Confidence source** | `DeterministicConfidenceSource` only — no floats. |
| **Ambiguity class** | Bounded bucket from `bounded-ambiguity-law.md`; `none` is explicit. |
| **Continuity lineage** | References to org continuity bridges when cross‑system (Phase **04**). |
| **Replay posture** | `replay_equivalent` \| `replay_degraded` \| `replay_partial` \| `replay_unverifiable` \| `replay_conflicted` (align golden‑thread corpus). |
| **Degradation semantics** | `none` \| `chronology` \| `causal` \| `continuity` \| `composite` + rule ids. |

## Survivability

Artifacts **survive** downgrade: provenance is never stripped to “fix” UI — only additional degradation receipts append.
