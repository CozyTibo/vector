# Retrieval & Query Layer Architecture

## Input Contracts
- Reasoning + memory artifacts
- Query intent
- Permission scope

## Output Contracts
- Context packs
- Retrieval provenance maps
- Selection confidence metadata

## Allowed Logic
- Contract validation and schema version checks.
- Deterministic transformation inside declared ownership.
- Confidence annotation only when phase contract requires it.

## Forbidden Logic
- No memory mutation
- No hidden ranking without traceability
- No final synthesis phrasing

## Dependency Boundary
This phase depends only on upstream-adjacent contracts and shared schema definitions. Direct dependency on non-adjacent phase internals is forbidden.
