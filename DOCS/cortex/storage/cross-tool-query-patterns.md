# Cross-Tool Query Patterns

## Objective
Define realistic cross-tool cognition queries and expose their join/traversal pressure before implementation.

## Representative Queries
- all discussions linked to deployment X across Slack, PRs, tickets, and docs,
- all blockers linked to initiative Y across planning and execution tools,
- all ownership transitions connected to incident Z and resulting actions.

## Core Complexity
- source ID heterogeneity by connector,
- identity resolution joins across tool namespaces,
- temporal and provenance filters at each traversal hop.

## Risk Patterns
- fanout when one anchor maps to many cross-tool artifacts,
- over-joining due to weakly selective predicates,
- repeated cross-tool traversals without cached adjacency hints.

## Index Priorities
- cross-tool identity resolution keys,
- relationship edge selectors,
- timeline-constrained linkage selectors.

## Guardrail
Cross-tool queryability is not optional debug ergonomics; it is a core capability of organizational cognition.
