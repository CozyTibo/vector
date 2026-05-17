# Phase 08 — Failure & degradation taxonomy

**Status:** normative.  
**Codes:** **SD-*** (Synthesis Degradation).  
**Mirror:** propagates Phase **07** **RD-*** as **SD-UPSTREAM-***.

---

## SD-* registry (v1 closed set)

| Code | Semantics | `omission_semantics` |
| ---- | --------- | -------------------- |
| `SD-CAP-CLAIMS` | max_claims exceeded | omitted_cap |
| `SD-CAP-RETRIEVAL` | max_retrieval_subqueries exceeded | omitted_cap |
| `SD-CAP-LLM` | token cap exceeded | omitted_cap |
| `SD-CITE-GAP` | claim could not cite | omitted_evidence |
| `SD-SCOPE-EMPTY` | zero hits lawful empty scope | omitted_empty_scope |
| `SD-UPSTREAM-RD` | generic upstream RD propagation | omitted_upstream |
| `SD-UPSTREAM-LEG` | retrieval legality floor | omitted_upstream_legality |
| `SD-LLM-TIMEOUT` | model timeout | omitted_llm |
| `SD-LLM-SCHEMA` | invalid JSON / schema | omitted_llm |
| `SD-LLM-POLICY` | model refused policy | omitted_llm |
| `SD-REPLAY-TWIN` | structural twin mismatch | omitted_replay |
| `SD-REPLAY-DRIFT` | pin drift detected | omitted_replay |
| `SD-POLICY-MISMATCH` | digest mismatch | omitted_policy |
| `SD-PUBLISH-BLOCKED` | publish barrier failed | omitted_publish |
| `SD-PIPELINE-GAP` | phase 07 not complete | omitted_pipeline |
| `SD-TEMPORAL-PIN` | temporal pin unresolved | omitted_temporal |

### RD → SD propagation map (deterministic)

| RD-* | SD-* |
| ---- | ---- |
| `RD-TCRE-GAP` | `SD-UPSTREAM-RD` + detail `rd_code` |
| `RD-REPLAY-UNSAFE` | `SD-UPSTREAM-LEG` |
| `RD-REPLAY-TWIN` | `SD-REPLAY-TWIN` |
| `RD-INDEX-STALE` | `SD-PIPELINE-GAP` |
| (all RD-*) | `SD-UPSTREAM-RD` with `upstream_rd` field |

---

## §Propagation

`apply_synthesis_degradation_taxonomy_v1(artifact, upstream_triggers)`:

1. Copy retrieval `retrieval_degradation_rollup` into `upstream_rollup` (read-only)
2. Append SD-* rows from synthesis phases
3. Compute `synthesis_degradation_posture` ∈ {`stable`, `degraded`, `critical`, `unresolved`}
4. Never collapse SD-* into silent `claims` removal — use `omitted_reason`

---

## substrate_health_state

| State | Condition |
| ----- | --------- |
| `healthy` | no SD-* critical, publication current |
| `degraded` | SD-UPSTREAM-* or SD-REPLAY-TWIN |
| `critical` | SD-PUBLISH-BLOCKED or SD-LLM-SCHEMA |
| `unresolved` | SD-SCOPE-EMPTY on default workload |
| `replay_conflicted` | SD-REPLAY-DRIFT |

Feeds overview pipeline synthesis stage (red/yellow/green).
