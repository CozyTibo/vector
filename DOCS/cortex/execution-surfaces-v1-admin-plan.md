# Execution Surfaces V1 — Admin Implementation Plan

**Status:** Implemented  
**Date:** 2026-06-01  

**Code:** `backend/src/vector/domains/cortex/execution_surfaces/` · `frontend/src/admin/executionSurfaces/`

---

## Phases (implementation order)

| Phase | Scope | Status |
|-------|--------|--------|
| **E0** | Docs, terminology, admin navigation, full Pydantic contracts | Done |
| **E1** | Backend read module + HTTP routes + unit tests | Done |
| **E2** | Frontend shell, default route, Domains + hero detail + Overview | Done |
| **E3** | People + Work (identity, artifact explorer, graph links panel) | Done |
| **E4** | Activity stream, connected work on overview, lifecycle filters | Done |
| **E5** | Fizzer verification checklist + smoke test script | Done |

---

## E0 — Docs + contracts

- [`execution-surfaces-v1-admin-plan.md`](execution-surfaces-v1-admin-plan.md) (this file)
- [`admin-navigation.md`](admin-navigation.md)
- [`00-overview/architecture.md`](00-overview/architecture.md) — Execution Surfaces consumer section
- [`00-overview/terminology-consistency.md`](00-overview/terminology-consistency.md) — Execution Surface term
- [`00-overview/drift-detection-checklist.md`](00-overview/drift-detection-checklist.md)
- [`scheduler-beat-tick-v1.md`](scheduler-beat-tick-v1.md) — admin default route note
- `contracts/admin.py` — `AdminExecutionSurface*` models including activity + lifecycle

---

## E1 — Backend

Module `execution_surfaces/`:

| File | Role |
|------|------|
| `omissions.py` | Footnotes + section omission helpers |
| `context.py` | Substrate advisories (graph backlog, calls deferred, …) |
| `lifecycle.py` | Planned / Active / Completed / Dormant buckets |
| `activity.py` | Observation activity stream (graph + membership only) |
| `connected_work.py` | Cross-tool chains |
| `domains.py` | Domain list + hero detail |
| `people.py` | Identity-based people |
| `work.py` | Artifact explorer |
| `overview.py` | Overview aggregates |
| `admin.py` | HTTP entry points |

**Routes:** `GET /cortex/execution-surfaces/{overview,domains,domains/:id,people,people/:id,work,work/:id,activity}`

**Tests:** `tests/vector/domains/cortex/execution_surfaces/`

---

## E2 — Frontend shell

- Default `/cortex` → `execution-surfaces`
- `AdminTenantCortexLayout` — Execution Surfaces first tab
- `AdminCortexExecutionSurfacesPage` + sub-routes for domain/work detail
- `DomainsTab`, `DomainDetailView` (hero)

---

## E3 — People + Work

- `PeopleTab` — list + detail, domains, participation counts
- `WorkTab` — filters, detail with `ExecutionArtifactLinks`

---

## E4 — Activity + connected work

- `ActivityTab` — filtered observation stream with footnotes
- Overview: connected work chains + recent observation sample
- Domain list: lifecycle filters

---

## E5 — Fizzer verification

- [`execution-surfaces-fizzer-verification.md`](execution-surfaces-fizzer-verification.md)
- `backend/scripts/execution_surfaces_smoke.py` — local smoke against tenant APIs

---

## Principles

1. **Read-only** — no passes, queues, schedulers, new tables  
2. **Transparent omissions** — every empty section explains why  
3. **Observation ≠ execution** — footnotes on all activity metrics  
4. **Hero = domain detail** — full provenance without opening substrate tabs  

---

## Success test

Operator answers who / what / what changed / why grouped from Execution Surfaces with provenance. Weak surfaces → improve substrate, not intelligence.
