# Cross-Phase Lifecycle

## End-To-End Event Lifecycle
1. Connector fetches source payload and emits ingestion envelope.
2. Ingestion validates envelope and persists raw immutable event.
3. Canonical maps raw event into organizational primitives.
4. Entity resolution links actors/artifacts/threads/projects.
5. Graph builds temporal relationships and state transition edges.
6. Memory layer compacts and derives query-focused views.
7. Reasoning generates deterministic and bounded AI inference artifacts.
8. Retrieval constructs bounded evidence context packs.
9. Synthesis produces explainable outputs with confidence metadata.

## Responsibility Transition Rules
- Every transition must carry provenance refs and version metadata.
- No transition may drop tenant scope.
- No transition may collapse uncertainty into forced certainty.

## Replay Path
Replay may start at raw layer and reflow downstream, or start at canonical/inference layers when upstream contracts are unchanged and replay safety criteria are satisfied.
