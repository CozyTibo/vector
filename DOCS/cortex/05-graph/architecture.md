# Organizational Graph Layer Architecture

## Input Contracts
- Resolved entities
- Canonical relations
- Temporal transition artifacts

## Output Contracts
- Temporal graph edges
- Lineage paths
- State transition adjacency

## Allowed Logic
- Contract validation and schema version checks.
- Deterministic transformation inside declared ownership.
- Confidence annotation only when phase contract requires it.

## Forbidden Logic
- No summarization output formatting
- No AI-generated truth assertions
- No source connector logic

## Dependency Boundary
This phase depends only on upstream-adjacent contracts and shared schema definitions. Direct dependency on non-adjacent phase internals is forbidden.
