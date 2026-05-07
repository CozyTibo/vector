# Operational Scale Assumptions

## Expected System Scale
- Multi-tenant operation with heterogeneous connector depth.
- Millions of events per tenant over multi-year history.
- High-volume replay windows during schema/model upgrades.
- Rapid relation growth from cross-tool linking.

## Throughput And Storage Implications
- Ingestion must handle bursty connector backfills.
- Raw event and canonical indexes must remain replay-efficient.
- Graph relation counts may grow superlinearly with tooling breadth.
- Derived memory compaction is required for retrieval latency bounds.

## Retrieval Complexity
Retrieval cost grows with memory depth and graph fanout; bounded context-pack policies are required to prevent query explosion.

## Planning Implication
Capacity planning and replay planning are first-order architecture concerns, not post-launch optimizations.
