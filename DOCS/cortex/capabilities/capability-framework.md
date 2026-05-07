# Capability Framework

## Definition: Cortex Capability

A Cortex capability is an **architecture-dependent cognition workflow** that emerges from the combined behavior of:

- replayable ingestion memory,
- canonicalized organizational entities/relations,
- identity continuity/linkage,
- temporal state reconstruction,
- provenance/confidence traceability,
- query/retrieval infrastructure,
- deterministic reasoning and bounded synthesis.

A capability is **not** a standalone prompt, chatbot response, or UI feature.

## Capability Unit

Every capability definition should include:

1. **Operational question class** it answers.
2. **Evidence substrate** it requires (raw/canonical/linkage/temporal).
3. **Reasoning mode** (deterministic vs bounded probabilistic synthesis).
4. **Trust contract** (provenance visibility, ambiguity representation, confidence semantics).
5. **Failure modes** (what can be wrong or incomplete and how that is surfaced).
6. **Replay expectations** (whether conclusions are stable under reprocessing/version drift).

## Capability Quality Gates

A capability should not be considered mature unless it satisfies:

- **Reconstruction gate:** can reconstruct evidence chain from outputs to source records.
- **Temporal gate:** can answer "when/what changed" without timeline collapse.
- **Continuity gate:** can preserve cross-tool actor/initiative continuity.
- **Trust gate:** can expose uncertainty and ambiguity, not hide them.
- **Replay gate:** can explain divergence across runs/versions.
- **Scale gate:** query patterns remain economically feasible at production volume.

## Maturity Levels

- **None:** architecture cannot represent the required primitives.
- **Low:** partial primitives exist, capability remains mostly manual/ad hoc.
- **Partial:** core primitives exist but major trust/temporal/query gaps remain.
- **Strong:** capability feasible for bounded workflows with known constraints.
- **High:** capability operationally reliable across large slices of org memory.

## Primitive Families Used In Mapping

- **Phase primitives:** ingestion, raw store, canonicalization, identity, graph, memory, reasoning, retrieval, synthesis, admin.
- **Ontology primitives:** actor/artifact/initiative/decision/dependency/blocker/discussion semantics.
- **Temporal primitives:** ordering, state transition history, period snapshots, timeline comparisons.
- **Linkage primitives:** identity resolution, cross-tool references, dependency edges, initiative continuity.
- **Trust primitives:** provenance chains, confidence typing, ambiguity persistence, explainability surfaces.
- **Replay primitives:** deterministic regeneration, versioned transforms, replay diff inspection.
- **Queryability primitives:** indexed paths, temporal traversal, provenance-aware retrieval, scale economics.
