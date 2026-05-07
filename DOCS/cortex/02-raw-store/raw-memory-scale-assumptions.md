# Raw Memory Scale Assumptions

## Purpose
Make implicit scale assumptions explicit so implementation can be validated against realistic growth.

## Assumption Ledger
| Dimension | Working Assumption | Architectural Implication |
| --------- | ------------------ | ------------------------- |
| Event growth | Sustained long-term growth with periodic spikes | Indexing and partition strategy must be evolution-ready. |
| Transcript growth | Highest payload growth driver | Hot payload retention must be selective; cold strategy is mandatory. |
| Payload size growth | Heavy-tailed distribution by connector/type | Metadata-first query paths are required for predictable latency. |
| Tenant growth | Increasing tenant count and skew | Tenant isolation and fairness controls are non-optional. |
| Replay frequency | Regular scoped replay, occasional broad replay | Replay scheduling and budget controls are required from v1. |
| Archival growth | Archive volume eventually exceeds hot volume | Rehydration path must be treated as first-class operational flow. |
| Indexing growth | Index count tends to drift upward over time | Index ownership and pruning policy required early. |

## Non-Assumptions
- Do not assume hot storage can remain default for all historical payloads.
- Do not assume broad replay is rare enough to ignore operational controls.
- Do not assume one index design fits replay + forensic + audit workloads.

## Validation Triggers
- Replay window latency slope growth,
- archive retrieval latency breaches,
- tenant skew causing queue starvation,
- index maintenance overhead reducing ingestion headroom.
