# Phase 07 — Retrieval admin control plane

**Status:** normative operator spec.

---

## §Surfaces (mandatory at closure)

| # | Surface | Operator answers |
| - | ------- | ---------------- |
| 1 | **Retrieval health strip** | Is retrieval replay-safe? Index epoch? Divergence count? |
| 2 | **Coverage panel** | eligible vs indexed vs queried |
| 3 | **Policy digest inspector** | Active `retrieval_policy_digest`, caps |
| 4 | **Query debugger** | Why this query returned these hits |
| 5 | **Provenance inspector** | Per-hit upstream digests + legality |
| 6 | **Replay inspector** | Twin run diff, `retrieval_query_replay_identity` |
| 7 | **Omission explorer** | `RD-*` classes + counts + triggers |
| 8 | **Temporal explorer** | `t_as_of`, windows, epoch pins |
| 9 | **Lineage chain explorer** | terminal → root chain |
| 10 | **Traversal binding panel** | walk_id, hop coverage, epoch match |
| 11 | **TCRE binding panel** | job id, chain id, chronology class |
| 12 | **Degradation topology** | Rollup graph of `RD-*` / upstream |
| 13 | **Query audit trail** | Historical receipts (filter legality) |
| 14 | **Legality matrix view** | R-LEG predicates + forbidden deployments |
| 15 | **Readiness economics** | Numeric receipt (mirror P05/P06) |
| 16 | **Control plane aggregate** | Queue depth, workload histogram |

---

## §Workflows

### W1 — Debug “why empty result?”

1. Open Query debugger → paste `retrieval_lookup_id` or compose envelope  
2. View **RESOLVE** phase output: addressing resolution trail  
3. Omission explorer → upstream class (`RD-TCRE-GAP`, etc.)  
4. Cross-link TCRE job or Graph stage from overview propagation  

### W2 — Verify replay safety before Phase 08 enablement

1. Run workload `replay_equivalence` with pins  
2. Replay inspector → must show zero divergence  
3. Legality matrix → R-LEG-01..07 green for tenant slice  

### W3 — Index rebuild (dangerous)

1. Scope: tenant + `index_epoch` bump  
2. Confirmation phrase per `10-admin/dangerous-action-safety-model.md`  
3. Job id + expected duration from readiness economics  

---

## §Operator questions (MUST be answerable without SQL)

| Question | Surface |
| -------- | ------- |
| Why was evidence excluded? | Omission explorer |
| What degraded? | Degradation topology + hit provenance |
| What replay posture existed? | Provenance inspector |
| What continuity guarantees? | TCRE binding + chronology class |
| What lineage path? | Lineage explorer |
| What traversal coverage? | Traversal binding panel |

---

## §RBAC

Align `10-admin/admin-permissions-model.md`:

- `cortex.retrieval.query` — execute queries  
- `cortex.retrieval.index_rebuild` — dangerous  
- `cortex.retrieval.read` — all GET surfaces  

---

## §UI routes (SPA)

| Route | Page |
| ----- | ---- |
| `.../cortex/retrieval` | Overview |
| `.../cortex/retrieval/query` | Query debugger |
| `.../cortex/retrieval/lineage/:kind/:ref` | Lineage explorer |
| `.../cortex/retrieval/control-plane` | Structural aggregate |
| `.../cortex/retrieval/audit` | Query audit trail |

Nav: enabled when `retrieval_runtime_legality` allows (see runtime legality matrix).
