# Terminology Consistency Audit

## Purpose
This document defines Cortex's canonical vocabulary and flags deprecated or forbidden wording. Terminology drift is architecture drift.

## Audit Findings (Current Pass)
- `confidence` (single field) and `confidence_score/confidence_band` were both present. Standardized to `confidence_score` + `confidence_band`.
- `model_version` and `inference_version` were both present. Standardized to `inference_version`.
- `inference_timestamp` and `inferred_at` were both present. Standardized to `inferred_at`.
- `object` was used in concept descriptions; standardized to `artifact` or `entity`.
- `risk` and `concern` were sometimes interchangeable; clarified as related but distinct concepts.

## Canonical Terms (Preferred)
- `Project`: bounded execution container with scope, timeline, ownership. Canon entity; may seed a **Declared Domain**.
- `Initiative`: strategic container spanning multiple projects. Canon entity; may seed a **Declared Domain**.
- `Execution Scope`: umbrella for materialized concern groupings — always qualify **Declared** vs **Emergent**.
- `Declared Domain`: deterministic cross-tool projection from a declared container seed. **V1.** Code: `declared_domains`, pass `declared_domain_pass`.
- `Declared container` / `declared_container_kind`: provider-agnostic seed classification set in **canon** (`canon/declared_container_registry.py`). Declared Domains reads this; no per-connector logic in domain module.
- `Emergent Domain`: future hybrid projection for undeclared organizational concerns. **Not V1.** Sibling to Declared Domains.
- `Execution Intelligence`: inferred interpretation (risk, drift, delivery) **on** scope layers — not scope materialization.
- `Execution Surface` / `Execution Surfaces`: read-only admin (and future product) composition over canon, identity, graph, and declared domains — human execution reality; not a substrate pass.
- `Artifact`: durable work object (code, doc, ticket, transcript, runbook).
- `Concern`: unresolved objection, risk signal, or uncertainty raised by participants.
- `Risk`: projected negative outcome; modeled as a concern subtype when evidence is predictive.
- `Discussion`: communication activity across one or more channels.
- `Thread`: temporally linked subset of discussion events with shared context.
- `CanonicalEvent`: tool-agnostic organizational event record.
- `CanonicalEntity`: normalized identity object (actor/team/project/artifact/topic/etc.).
- `CanonicalRelation`: typed relationship between canonical entities.
- `Ownership`: accountable relation.
- `Responsibility`: expected obligation within a role/time window.
- `Memory Layer`: any persisted representation used for retrieval/reasoning.
- `Derived Memory`: non-authoritative projection derived from canonical/graph.
- `Inference`: confidence-scored non-deterministic output.
- `Provenance`: lineage metadata proving evidence chain continuity.

## Deprecated Terms (Replace During Edits)
- `object` -> use `artifact` or `entity` depending semantics.
- `activity` -> use `CanonicalEvent` unless intentionally generic.
- `summary truth` -> use `synthesis artifact` (non-authoritative).
- `AI result` -> use `inference artifact` with confidence semantics.

## Forbidden Terms (execution scope)
- `Topic` / `Topic Materialization` for execution-scope layers.
- `Declared Work Rollup` — renamed to **Declared Domain**.
- `Execution Domain` as V1 name — use **Declared Domain**; reserve umbrella for **Execution Scope**.
- `Emergent Execution Domain` — use **Emergent Domain**.

## Forbidden Terms
- `AI truth`
- `autonomous memory`
- `final certainty` (without confidence and evidence references)
- `smart connector` (connectors are adapters only)
- `context dump` as retrieval strategy

## Overload Resolution Rules
- `Declared Domain` vs `Initiative`/`Project`: initiative/project are **canon seeds**; Declared Domain is the **cross-tool projection**.
- `Declared Domain` vs `Emergent Domain`: declared = provider seed + deterministic expansion; emergent = no seed, hybrid (future).
- `Execution Scope` vs `Execution Intelligence`: scope = what belongs together; intelligence = what it means for delivery/risk.
- `Project` vs `Initiative`: project is execution-bounded; initiative is strategic and multi-project.
- `Discussion` vs `Thread`: discussion is broad communication set; thread is linked sub-sequence.
- `Ownership` vs `Responsibility`: ownership implies accountability relation; responsibility implies expected action scope.
- `Concern` vs `Risk`: concern can be unresolved with low confidence; risk is concern with projected impact framing.
- `Entity` vs `Actor`: actor is an entity subtype.

## Wording Policy
- Use `deterministic` for extraction or mapping backed by explicit rules.
- Use `inferred` for heuristic/AI outputs.
- Use `superseded` for replaced records; never say "overwritten".
- Use `replay` for deterministic reconstruction from persisted inputs and versions.

## Enforcement
Every schema or architecture PR touching Cortex docs must confirm compliance with this terminology document and `drift-detection-checklist.md`.
