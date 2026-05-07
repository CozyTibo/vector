# Raw Memory Performance Risks

## Ranked Risk Register
| Risk | Severity | Probability | Operational Impact |
| ---- | -------- | ----------- | ------------------ |
| Broad replay scan saturation | High | Medium | Replay and ingestion contention, delayed trust recovery. |
| Archive rehydration bottlenecks | High | Medium | Replay/forensics latency spikes on cold history. |
| Query plan instability on deep windows | High | Medium | Unpredictable operator and replay query latency. |
| Replay queue saturation under concurrency | High | Medium | Tenant fairness degradation and backlog growth. |
| Index amplification on raw hot tables | Medium | High | Ingestion latency regression and maintenance pressure. |
| Large transcript payload retrieval pressure | Medium | High | IO-heavy diagnostics and slower incident workflows. |
| Corruption scan overreach | Medium | Medium | Expensive integrity workflows if not scoped. |
| Temporal retrieval over-breadth | Medium | Medium | Forensic timelines become slow/noisy. |

## Top Three Immediate Controls
1. Enforce replay scope limits and quota-based scheduling.
2. Keep metadata-first retrieval and lazy payload hydration defaults.
3. Instrument and alert on query class p95/p99 and queue depth.
