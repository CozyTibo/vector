# Storage Architecture Review

## Goal
Challenge whether Cortex can stay queryable under long-horizon organizational cognition workloads without prematurely introducing additional infrastructure.

## What Must Stay True
- deterministic replay remains possible from persisted source-of-truth data,
- provenance paths remain inspectable end-to-end,
- temporal reconstruction remains operationally usable for humans,
- cross-tool continuity queries remain bounded enough for production debugging.

## Current Architecture Strengths
- PostgreSQL is operationally mature and excellent for transactional correctness.
- Append-oriented ingestion and event persistence align well with relational durability.
- Tenant-scoped boundaries and deterministic contracts support safe replay semantics.
- Consistency guarantees are stronger than most distributed multi-store alternatives.

## Critical Stress Areas
- replay scans over years of history,
- recursive provenance traversal through multi-phase derivations,
- lineage exploration with branching continuity and ambiguity states,
- temporal as-of reconstruction with supersession semantics,
- mixed workloads (hot ingest + long scans + operator diagnostics).

## Where PostgreSQL Is Strong
- write correctness and referential integrity,
- narrow-scope OLTP retrieval,
- deterministic ordered processing windows,
- governance/auditability at schema and migration levels.

## Where PostgreSQL Can Degrade
- recursive deep traversal with high fanout joins,
- broad historical scans competing with live write-heavy paths,
- index sprawl and write amplification on multi-dimensional query needs,
- unstable execution plans for highly variable query parameter shapes.

## Dangerous Assumptions To Reject
- "current performance implies future performance" under 100x scale growth,
- "one index strategy can serve replay + lineage + temporal queries equally",
- "queryability can be solved later without reshaping persistence boundaries",
- "graph-like workloads stay shallow in organizational memory systems."

## Recommended Governance
- classify query families early and instrument each separately,
- define explicit thresholds for when optimization is insufficient,
- require replay/provenance integrity sign-off before any storage evolution,
- treat operator diagnostic query latency as product-critical reliability signal.
