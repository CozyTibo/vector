# Cortex Admin Navigation

## Default experience

`/admin/tenants/{tenant_id}/cortex` redirects to **Execution Surfaces** — the human-facing execution reality view.

## Tab order (mental model)

```text
Execution Surfaces   ← product (who, what, why grouped)
────────────────
Declared Domains     ← scope materialization ops
Links (Graph)        ← relationship extraction ops
Identities           ← identity reconciliation ops
Canonical            ← canon materialization ops
Ingestion            ← exhaust + sync ops
```

## Execution Surfaces sub-navigation

| Sub-tab | Route | Purpose |
|---------|-------|---------|
| Domains | `?tab=domains` | Declared domain list + lifecycle filters |
| Domain detail | `/execution-surfaces/domains/:domainId` | **Hero** — work, people, chains, evidence |
| Overview | `?tab=overview` | Summary + sample chains + recent observation |
| People | `?tab=people` | Identity-based participation |
| Work | `?tab=work` | Artifact explorer |
| Activity | `?tab=activity` | Observation signal stream (not execution timeline) |

## When to use substrate tabs

| Question | Tab |
|----------|-----|
| Why is domain membership empty? | Declared Domains (pass, pins) or Graph |
| Why is person unresolved? | Identities |
| Why is artifact not materialized? | Canonical / Ingestion |
| What is the org doing? | **Execution Surfaces** |
