# Linkage Cost Model

## Cost Drivers
- cross-tool candidate generation volume,
- ambiguity persistence and review overhead,
- replay/reprocessing of linkage-heavy scopes,
- confidence and conflict computation overhead.

## Scaling Risks
- candidate explosion for high-activity workspaces,
- ambiguity backlog growth,
- continuity recomputation costs during ontology/version changes.

## Cost Guardrails
- prioritize deterministic pruning before inference,
- scope replay/reprocessing precisely,
- monitor ambiguity aging and conflict queue growth as cost signals.
