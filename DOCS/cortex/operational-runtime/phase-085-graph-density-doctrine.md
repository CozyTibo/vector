# Phase 08.5 — Graph density & continuity expansion

**Status:** normative.  
**Implements:** Steps 10–13 · **G-P085-GRAPH-01**, **G-P085-PROMO-01**, **G-P085-ORPHAN-01**.

---

## Problem statement

Mock and early tenants show **high orphan artifact counts** and **pending link candidates** with **low promoted `CortexOrgLink` density**, blocking traversal and downstream stages.

---

## Density metrics

| Metric | Definition |
| ------ | ---------- |
| `graph_promoted_edge_count` | authoritative org links |
| `graph_candidate_count` | pending candidates |
| `graph_orphan_artifact_count` | artifacts without connecting edge |
| `graph_connectivity_ratio` | promoted / (promoted + orphans) |
| `graph_density_score` | weighted composite 0–100 |

---

## Lawful growth (**G-P085-PROMO-01**)

**Allowed:**

- Promote link candidates passing Phase 04 merge governance + replay checks
- Stitch continuity from canonical identity anchors (deterministic rules)

**Forbidden:**

- Probabilistic edge invention
- Promotion without `org_link_replay_job` receipt when policy requires

**Scheduler:** `schedule_graph_density_pass_v1` after phase 04 or on backlog threshold.

---

## Orphan law (**G-P085-ORPHAN-01**)

Orphans MUST be classified:

| Class | Action |
| ----- | ------ |
| `orphan_awaiting_promotion` | enqueue candidate promotion |
| `orphan_identity_unresolved` | block; surface in identity console |
| `orphan_disconnected_component` | traversal blocked; RET-SKIP-GRAPH-DISCONNECTED |
| `orphan_intentionally_excluded` | document in omission |

---

## Continuity maturity stages (graph)

| Stage | Criteria |
| ----- | -------- |
| **G0** | orphans > 50% artifacts |
| **G1** | connectivity_ratio ≥ 0.3 |
| **G2** | connectivity_ratio ≥ 0.7 |
| **G3** | zero pending candidates blocking traversal |

---

## Completeness propagation

Update graph stage envelope:

- `substrate_state = degraded` when orphans block traversal propagation (already partial)
- Add `graph_density_score` to metrics
- **Fake-green fix:** if `orphan_artifacts > 0` AND `pending_link_candidates > θ`, state MUST NOT be `healthy`
