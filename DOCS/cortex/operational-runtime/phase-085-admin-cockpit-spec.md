# Phase 08.5 — Admin operational cockpit specification

**Status:** normative.  
**Implements:** Steps 30–32 · **G-P085-CP-01..03**.

---

## Design principle

Transform Cortex admin overview from **stage cards** into a **truthful operational command center** — no AI theater, no decorative analytics.

All numbers MUST reconcile to DB queries documented per surface.

---

## Surfaces (16 + 3 new = 19 operational)

| # | Surface | Route (tenant) | Purpose |
| - | ------- | -------------- | ------- |
| 1 | **Operational command center** | `/cortex/operational` | maturity radar, health dimensions, next action |
| 2 | **Pipeline progression timeline** | `/cortex/substrate-pipeline/timeline` | phases 02–08 with timestamps + continuation |
| 3 | **Stalled substrate explorer** | catalog + tenant | WAITING/STALLED rows + recover |
| 4 | **Continuation inspector** | `/substrate-pipeline/continuation` | nonce, receipts, heartbeats |
| 5 | **Retrieval starvation explorer** | `/cortex/retrieval/starvation` | reports, RET-SKIP histogram |
| 6 | **Retrieval density trends** | `/cortex/retrieval/density` | acceptance rate, empty epoch rate |
| 7 | **Graph density explorer** | `/cortex/graph/density` | orphans, candidates, promotion queue |
| 8 | **Traversal pending explorer** | `/cortex/traversal/pending` | walks, blockers |
| 9 | **TCRE saturation explorer** | `/cortex/reasoning/saturation` | pending reconstructions |
| 10 | **Synthesis activation explorer** | `/cortex/synthesis/activation-audits` | scopes vs jobs |
| 11 | **Why synthesis empty** | `/cortex/synthesis/eligibility/why-empty` | panel messages |
| 12 | **Eligibility explain** | `/cortex/synthesis/eligibility/explain` | structured blockers |
| 13 | **Recovery action console** | POST recover endpoints | policy-gated |
| 14 | **Causal failure chain** | embedded in timeline | degradation propagation path |
| 15 | **Substrate heatmap** | `/cortex/operational/heatmap` | stage × health grid |
| 16 | **Runtime maturity dashboard** | `/cortex/operational/maturity` | 6 dimensions + class |
| 17 | **Replay divergence strip** | cross-link synthesis/retrieval | existing explorers |
| 18 | **Density trend charts** | 7d rollups (DB-backed) | not ephemeral only |
| 19 | **Operational health API** | `/substrate-pipeline/operational-health` | aggregate JSON |

**Partial shipped (backend):** 4, 5, 11, 12, 16 (API), stalled catalog.

---

## Overview integration (**G-P085-CP-03**)

Replace misleading **healthy + 0 objects** with:

```
[ maturity: PROGRESSING ]  [ starvation: RETRIEVAL ]  [ stall: TCRE wait 42m ]
```

Each stage card adds:

- `classification`: idle | starved | progressing
- `next_required_step` (from explain APIs)
- link to explorer

---

## Progression timeline

Per pipeline run:

```
02 ✓ 03 ✓ 04 ✓ 05 ✓ 06 ⏳ TCRE(job=…) 07 — 08 —
         ↑ continuation WAITING since T0
```

---

## Recovery actions (RBAC dangerous)

| Action | Gate |
| ------ | ---- |
| Recover stalled pipeline | admin + confirm |
| Force resume phase 07 | admin + lawful check |
| Trigger graph promotion pass | admin |
| Trigger traversal batch | admin |
| Trigger TCRE saturation | admin |

---

## Forbidden UI patterns

- Semantic summaries not tied to receipts
- Success % without denominator
- Hiding `reconstruction_not_yet_run` behind green TCRE card
