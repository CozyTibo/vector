# Raw Memory Cost Model

## Cost Drivers
- payload volume growth (especially chat + transcripts),
- replay scan frequency and scope size,
- index maintenance overhead,
- archival storage and rehydration transfer costs.

## Hot vs Cold Economics
- hot storage optimized for replay latency but expensive.
- cold storage optimized for cost but slower retrieval.
- archival strategy must balance replay SLO against storage spend.

## Cost Guardrails
- enforce retention classes and archival transitions.
- monitor large payload concentration and transcript growth.
- avoid low-value indexes on high-write raw tables.
- budget broad replay jobs before execution.

## Replay Cost Awareness
- replay-heavy periods can shift cost profile from storage-dominant to scan-dominant.
- replay planning must include resource budget and priority controls.

## Practical Cost Controls
1. use scoped replay by default,
2. cap concurrent archive rehydration jobs,
3. apply index ownership policy (query-owned indexes only),
4. separate trust-critical replay budget from routine reprocessing budget.
