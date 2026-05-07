# AI Boundary Enforcement Map

## Purpose
Define exactly where AI is allowed, where it is forbidden, and what contract obligations apply.

## Deterministic-Only Zones (AI Forbidden)
- `01-ingestion`: fetch, validate, normalize envelope.
- `02-raw-store`: immutable persistence and replay indexing.
- `03-canonical`: deterministic mapping to canonical contracts.
- Core portions of `04-entity-resolution`: deterministic identity evidence collection.

## AI-Assisted Zones (Bounded)
- `04-entity-resolution` (bounded disambiguation only with explicit uncertainty).
- `07-reasoning` (causal hypothesis generation, ambiguity resolution).
- `08-retrieval` (semantic retrieval assistance, never authoritative ranking without traceability).
- `09-synthesis` (narrative assembly and summarization with evidence citations).

## Allowed AI Usage
- semantic topic linking,
- ambiguity classification,
- concern phrasing normalization,
- causal hypothesis generation,
- bounded summarization.

## Forbidden AI Usage
- creating raw facts,
- mutating canonical truth directly,
- bypassing provenance requirements,
- resolving conflicting evidence silently,
- acting as connector intelligence.

## Contract Dependencies
- required fields on inferred artifacts:
  - `inference_type`
  - `inference_version`
  - `inferred_at`
  - `confidence_score`
  - `confidence_band`
  - `supporting_evidence_refs`
  - `ambiguity_reason` when unresolved
  - `replay_version`

## Lifecycle Dependencies
- AI can run only after deterministic extraction and ambiguity marking.
- AI outputs remain non-authoritative and cannot bypass supersession lifecycle.

## Replay Dependencies
- AI outputs are replay-sensitive and must be comparable across `inference_version` changes.
- replay must preserve provenance and confidence evolution, not overwrite history.

## Governance Enforcement
- Any expansion of AI into deterministic-only zones requires:
  - architecture review,
  - AI-boundary review,
  - replay impact review,
  - ADR approval.
