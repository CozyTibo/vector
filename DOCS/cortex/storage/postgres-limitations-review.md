# Postgres Limitations Review

## Objective
Be explicit about where PostgreSQL supports Cortex strongly and where it may fail under cognition-scale workloads.

## Strong Fit Areas
- transactional correctness and isolation,
- append-heavy ingestion and canonical persistence,
- schema-governed evolution and auditability,
- deterministic replay baselines.

## Limitation Areas
- deep recursive graph-like traversals at large fanout,
- broad historical scans under concurrent live writes,
- index sprawl causing significant write amplification,
- variable query parameter patterns causing plan instability.

## Operational Pain Scenarios
- frequent full-history replays with active ingestion,
- incident windows requiring rapid deep lineage traversal,
- long-window temporal reconstructions with supersession.

## What This Means
PostgreSQL remains the correct baseline, but not an excuse to defer query family modeling and threshold-driven acceleration planning.
