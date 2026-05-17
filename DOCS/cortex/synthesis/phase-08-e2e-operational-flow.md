# Phase 08 — E2E operational flow (operator & certification)

**Status:** normative.  
**Proves:** ingest → intelligence without manual bootstrap.

---

## Scenario A — Happy path (single connector tenant)

### Preconditions

- Phase **01** exhaust minimum for one connector (§2.5 matrix partial OK)
- Canonical bundle materializable
- Pipeline enabled: phases **02–08**

### Steps

| # | Actor | Action | Expected |
| - | ----- | ------ | -------- |
| 1 | System | Connector sync completes | Raw rows persisted |
| 2 | System | `schedule_substrate_pipeline_v1` fires | Coordinator task queued |
| 3 | Operator | Overview shows pipeline run `running` | Phases 02–07 visible |
| 4 | System | Phase **07** completes | `published_index_epoch` set |
| 5 | System | Phase **08** completes | `synthesis_publication_epoch` set |
| 6 | Operator | Open Synthesis control plane | `surface_kind=runtime_backed` health green/degraded |
| 7 | Operator | Open artifact for `pipeline_default` | Claims + citations present |
| 8 | Operator | Citation explorer | Each claim links to retrieval hit |
| 9 | Harness | `G-P08-REPLAY-01` twin | Structural pass |

### Artifacts produced

- ≥1 `SynthesisIntelligenceArtifactV1` per default scope
- `synthesis_job_receipt` with full `execution_trace`
- Pipeline phase **08** receipt on run row

---

## Scenario B — Upstream degradation (TCRE gap)

| # | Action | Expected |
| - | ------ | -------- |
| 1 | Tenant with incomplete TCRE | Retrieval returns `RD-TCRE-GAP` |
| 2 | Synthesis runs | `SD-UPSTREAM-RD` rows |
| 3 | Legality | `synthesis_degraded` (not forbidden) |
| 4 | Claims | Causal claims omitted; degradation_brief populated |
| 5 | Publish | Allowed if policy `allow_degraded_publish=true` |

---

## Scenario C — Replay verification (pre-Phase 09)

| # | Action | Expected |
| - | ------ | -------- |
| 1 | Operator runs workload `replay_equivalence_synthesis` | Two structural twins |
| 2 | Replay explorer | Zero citation set diff |
| 3 | Legality matrix | S-LEG predicates green |

---

## Scenario D — Concurrent ingest (stress)

| # | Action | Expected |
| - | ------ | -------- |
| 1 | Two pipeline runs debounced | Single coordinator wins |
| 2 | Second run after first completes | New synthesis epoch |
| 3 | Idempotency | Same `idempotency_key` → same artifact id |

---

## Certification bundle (SYNTHESIS-CERT-PACK-1)

Archives:

- Tenant verification slice output
- Golden vector results
- Sample artifacts (redacted LLM traces)
- Policy pack digest
- Pipeline phase **08** receipt copy

Gate **G-P08-CLOSE-01** — see [`phase-08-closure-gates-doctrine.md`](./phase-08-closure-gates-doctrine.md).

---

## E2E test modules (implementation)

| Test file | Scenario |
| --------- | -------- |
| `test_phase08_e2e_pipeline_default.py` | A |
| `test_phase08_e2e_degraded_upstream.py` | B |
| `test_phase08_e2e_replay_twin.py` | C |
| `test_phase08_e2e_pipeline_idempotency.py` | D |

Location: `backend/tests/vector/domains/cortex/synthesis/e2e/` (future).

Harness helpers: `vector.domains.cortex.synthesis.testing` (mirror retrieval testing package).
