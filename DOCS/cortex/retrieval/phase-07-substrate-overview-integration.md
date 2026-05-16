# Phase 07 — Substrate overview integration plan

**Status:** normative (admin UX + API contract).

---

## Pipeline card (7th stage)

Order:

```text
Raw exhaust → Canonical → Identity → Graph → Traversal → TCRE → Retrieval
```

### Card fields (match existing `SubstrateCompletenessStage`)

| Field | Retrieval semantics |
| ----- | ------------------- |
| `total_objects` | `eligible_artifact_count` (or indexed when never built — see completeness doctrine) |
| `success_percent` | `replay_safe_query_percent` OR `coverage_percent` when no queries yet |
| `degraded_percent` | queries with `retrieval_degraded` |
| `unresolved_percent` | `RD-ADDRESSING` / index gaps |
| `intentionally_excluded_count` | pending index builds |
| `replay_posture` | aggregate from health |
| `omission_classes` | §completeness doctrine |

### Detail route

`/admin/tenants/{tenant_id}/cortex/retrieval`

---

## Degradation propagation panel

Extend `build_degradation_propagation_chain_v1` rules (see degradation taxonomy table).

Examples:

- `reconstruction_coverage_gap` (tcre) → retrieval as `RD-TCRE-GAP`  
- `traversal_never_executed` → retrieval as `RD-TRAVERSAL-IDLE`  
- `orphan_artifacts` → retrieval as `RD-GRAPH-ORPHAN`

---

## Operator drill-down path

Overview card click → Retrieval admin Overview →

1. Coverage strip (eligible vs indexed)  
2. Last 10 query receipts (legality badge)  
3. Link to Query debugger / Lineage explorer  

---

## Cortex nav

`AdminTenantCortexLayout` section:

```text
{ key: "retrieval", label: "Retrieval", enabled: true }
```

Position: after `reasoning` (TCRE), before `synthesis` (disabled until Phase 08).

---

## API endpoints (admin, planned)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `.../cortex/retrieval/legality` | Matrix + policy digest |
| GET | `.../cortex/retrieval/coverage` | Completeness metrics |
| POST | `.../cortex/retrieval/query` | Execute envelope |
| GET | `.../cortex/retrieval/queries/{receipt_digest}` | Audit replay |
| GET | `.../cortex/retrieval/lineage/...` | Lineage explorer |
| GET | `.../cortex/retrieval/control-plane` | Structural aggregate |
| GET | `.../cortex/retrieval/readiness-economics` | Numeric receipts |

Cross-link substrate completeness: ledger includes retrieval stage from `project_retrieval_completeness_v1`.
