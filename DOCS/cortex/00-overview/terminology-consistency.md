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
- `Project`: bounded execution container with scope, timeline, ownership.
- `Initiative`: strategic container spanning multiple projects.
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

## Forbidden Terms
- `AI truth`
- `autonomous memory`
- `final certainty` (without confidence and evidence references)
- `smart connector` (connectors are adapters only)
- `context dump` as retrieval strategy

## Overload Resolution Rules
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
