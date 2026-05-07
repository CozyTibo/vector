# Organizational Ontology

## Ontology Design Rules
- Definitions must be tool-agnostic.
- Concepts must support temporal state transitions.
- Concepts must map to deterministic contracts before AI inference.

## Core Concepts
- **Project**: bounded execution container with explicit scope, timeline, and ownership.
- **Initiative**: multi-project strategic intent spanning time and teams.
- **Topic**: recurring semantic theme emerging from discussions, docs, and tickets.
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
