# Queryability At Scale Review

## Objective
Define the hardest query workloads Cortex must support and challenge whether the current model can satisfy them under real growth.

## High-Pressure Query Families
- initiative evolution over 12-24 months including superseded states,
- ownership transition timelines across teams and tools,
- incident lineage reconstruction (discussion -> code -> ticket -> doc),
- decision provenance evidence chain reconstruction,
- ambiguity evolution and resolution history inspection.

## Complexity Drivers
- cross-domain joins (raw/canonical/linkage/provenance/replay),
- temporal range filters on large historical windows,
- recursive expansion depth variability,
- high-fanout identity and artifact relationships.

## Operational Failure Modes
- joins degrade from index-assisted to scan-heavy plans,
- recursive CTE latency explodes under broad scope,
- replay diagnostics saturate storage IO,
- operator-facing trust workflows time out during incidents.

## Query Class Segmentation (Required)
- Class A: trust-critical operator debugging,
- Class B: replay control and validation,
- Class C: product cognition retrieval,
- Class D: exploratory analytics.

## Evaluation Criteria
- p95 latency stability per query class,
- query cost growth slope as time horizon expands,
- plan stability across parameter variation,
- contention impact on ingestion/replay throughput.

## Direction
Cortex should optimize by query family with targeted acceleration layers, not one generic storage tactic.
