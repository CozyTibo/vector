# ADR: Cortex ingestion transport (Phase 5)

**Status:** Accepted  
**Date:** 2026-05-28  

## Context

Cortex operational runtime uses Postgres (`cortex_passes`) for canon and identity passes. Ingestion remains connector I/O (HTTP to GitHub, Slack, etc.).

## Decision

**Option A — Ingestion stays on Celery** (`cortex_live`, `cortex_replay`).

| Lane | Transport |
|------|-----------|
| Ingestion | Celery tasks on dedicated ingestion worker |
| Canon / identity passes | `cortex_passes` + `orchestrator_tick` → `poll_passes` on cortex worker (`vector` queue) |
| Replay | `cortex_replay` queue, unchanged |

## Rationale

- Long-running HTTP syncs should not block pass polling on a shared loop.
- Ingestion already has mature min-gap, tick audit, and operator pause.
- Two ECS workers (ingestion + cortex) match cost and isolation goals.

## Consequences

- Beat runs only `vector.cortex.runtime.orchestrator_tick` on the cortex worker.
- Email/onboarding remain on `vector` queue alongside runtime tasks.
- Future graph/projection passes register as new `pass_type` values only.

## Not chosen

**Option B** (ingestion as `pass_type=ingestion_sync` in DB poll loop) — deferred; would merge workers at the cost of I/O blocking pass fairness.
