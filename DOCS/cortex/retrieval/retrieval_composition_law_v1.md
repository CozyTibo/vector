# Retrieval composition law (Phase S3.4)

Every **published** retrieval index epoch must satisfy the semantic mix gate and expose an operator receipt on phase 07 output and admin retrieval overview.

## Mix laws (fail-loud when gate enabled)

| Metric | Green threshold |
|--------|-----------------|
| `org_link_pct` | ≤ 30% |
| `org_entity_pct` | ≤ 10% |
| `execution_index_pct` | ≥ 60% (materialization, walk, causal_chain, causal_edge) |

Execution index kinds are **artifact-backed continuity** — not org-link topology mirrors.

## Published epoch receipt (`semantic_mix`)

Phase 07 `substrate_phase_receipt.detail` and publish finalize output include:

```json
{
  "semantic_mix": {
    "org_link_pct": 25.0,
    "execution_index_pct": 65.0,
    "org_entity_pct": 5.0,
    "entry_count": 420,
    "index_epoch": "epoch-…",
    "gate_pass": true
  }
}
```

## Materialization order (Wave S3)

1. walk  
2. tcre (includes causal_edge rows from S2.4 / S3.1)  
3. canonical materialization (island-scoped)  
4. org_link (capped; skipped when execution share ≥ 60% before pass)

## Operator surfaces

- `GET …/cortex/retrieval/overview` — `semantic_mix` + `index_kind_counts` for latest published epoch  
- Phase 07 pipeline receipt — `semantic_mix` in hashed detail  
- Mix gate implementation: `retrieval_semantic_mix_v1.py`  
- Publish barrier: `retrieval_publish_contract.py`

## Rollback

- Disable mix gate: settings / `cortex_retrieval_semantic_mix_gate_enabled`  
- org_link cap / skip: S3.2 env flags  
- causal_edge indexing: `CORTEX_RETRIEVAL_INDEX_TCRE_CAUSAL_EDGES=0`
