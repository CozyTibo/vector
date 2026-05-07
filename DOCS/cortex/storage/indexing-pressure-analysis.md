# Indexing Pressure Analysis

## Objective
Anticipate index sprawl and write amplification before schema hardening.

## Index Domains
- replay selectors,
- temporal range selectors,
- provenance traversal selectors,
- lineage/linkage selectors,
- tenant/connectors scope selectors,
- ambiguity and confidence triage selectors.

## Pressure Risks
- hot table write amplification from too many composite indexes,
- index bloat and maintenance lag under long retention,
- degraded plan quality from overlapping index candidates.

## Operational Symptoms
- increasing ingest latency with flat traffic,
- VACUUM/autovacuum lag and bloat growth,
- replay scans regressing into expensive plan paths.

## Governance Model
- Tier 1: integrity/replay-critical indexes (must keep),
- Tier 2: operator-critical indexes (review quarterly),
- Tier 3: convenience indexes (remove aggressively if low ROI).

## Guardrail
Every index requires an owning query family and observability metric; orphan indexes are technical debt by default.
