# Raw Queryability Review

## Objective
Validate that raw memory is practically queryable for operators and downstream phases without forcing semantic behavior into the raw layer.

## Core Raw Query Classes
| Query Class | Purpose | Risk At Scale |
| ----------- | ------- | ------------- |
| Replay retrieval | Fetch deterministic replay input windows | Large range scans and archive rehydration latency. |
| Provenance lookup | Resolve source evidence for derived records | High fanout source reference expansion. |
| Source-object retrieval | Investigate object-level source history | Object-key skew and uneven connector distributions. |
| Historical retrieval | Audit long-horizon event history | Deep-window latency and plan instability. |
| Corruption inspection | Verify integrity/hash mismatch paths | Expensive payload checks if not metadata-led first. |
| Timeline support | Hydrate chronology for higher phases | Broad-window ordering pressure. |

## Queryability Reality
- raw layer queryability is metadata-first, payload-second,
- high-scale usability depends on strong selector selectivity,
- query ergonomics degrade quickly when operators jump to unbounded windows,
- replay and forensic query classes can conflict without scheduling isolation.

## Expected Degradation Zones
- multi-month or multi-year cross-connector retrieval,
- repeated deep forensic drills on transcript-heavy tenants,
- broad replay + incident debugging happening concurrently.

## Practical Queryability Controls
1. Require bounded windows by default in operational surfaces.
2. Encourage progressive query expansion (small window -> widen).
3. Keep payload hydration lazy unless explicitly requested.
4. Track p95/p99 by query class, not only global query latency.
