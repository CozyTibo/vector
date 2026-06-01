# Organizational Ontology

## Ontology Design Rules
- Definitions must be tool-agnostic.
- Concepts must support temporal state transitions.
- Concepts must map to deterministic contracts before AI inference.

## Execution scope concepts (materialized projections)

These are **not** canon entity types. They are **projections** over canon + identity + graph. See [`execution-scope-architecture.md`](../execution-scope-architecture.md).

- **Declared Domain**: deterministic cross-tool rollup of a **declared container** with participants, mass, activity, momentum. **V1.** Materialized from canon seeds with `declared_container_kind`.
- **Declared container**: provider-agnostic work container (initiative, project, work database, …) — classified in canon, not in Declared Domains code.
- **Emergent Domain**: materialized grouping around a concern that may **never** be declared (e.g. Authentication, Hiring). **Future — hybrid.**
- **Execution Scope**: umbrella for Declared Domains + Emergent Domains.

## Core Concepts
- **Project**: bounded execution container with explicit scope, timeline, and ownership. May seed a **Declared Domain**.
- **Initiative**: multi-project strategic intent spanning time and teams. May seed a **Declared Domain**.
- **Topic** (canonical / legacy): recurring semantic theme in discussions — **not** execution scope. Do **not** use for Declared or Emergent Domains.
- **Decision**: explicit choice among alternatives with rationale and consequences.
- **Blocker**: condition materially preventing expected execution progress.
- **Ownership**: accountable relationship between actor/team and artifact, project, or concern.
- **Responsibility**: expected action obligation tied to role/time context.
- **Dependency**: execution relationship where one artifact/state relies on another.
- **Concern**: unresolved risk, objection, or uncertainty raised by participants.
- **Discussion**: conversational activity around one or more topics or decisions.
- **Thread**: temporally-linked sequence of discussion events with shared context.
- **Artifact**: durable work object (code change, spec, doc, ticket, transcript).
- **Milestone**: time-bounded outcome checkpoint with acceptance criteria.
- **Organizational Memory**: versioned, replayable, provenance-linked representation of organizational events, entities, relations, and inferred interpretations over time.

## Temporal Semantics
Concepts may change status over time (`open`, `resolved`, `superseded`, `deprecated`) and must preserve historical states rather than overwriting previous meaning.
