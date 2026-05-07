# Provenance And Confidence Semantics

## Canonical Confidence Model
- Numeric: `confidence_score` in `[0.0, 1.0]`.
- Categorical: `confidence_band` in `{low, medium, high}`.
- Uncertainty explanation: `ambiguity_reason` when confidence is not high.
- Evidence linkage: `supporting_evidence_refs[]` is mandatory for inferred artifacts.

## Deterministic vs Inferred Knowledge
- Deterministic: directly extracted from source with explicit parsing rules.
- Inferred: derived through heuristics or AI where ambiguity exists.
- Synthesis: narrative composition over deterministic + inferred artifacts.

## Provenance Philosophy
No claim without lineage. Every claim references evidence. Evidence references maintain stage-by-stage traceability from synthesis output back to raw source events.

## Provenance Minimum Fields
Every derived or inferred record must include:
- `provenance.chain_id`
- `provenance.input_refs[]`
- `provenance.source_refs[]`
- `provenance.transform_stage`
- `provenance.processor_version`
- `provenance.generated_at`
- `replay_version`

## Confidence Philosophy
Confidence reflects evidence sufficiency and ambiguity, not model persuasion quality. High confidence requires strong evidence consistency across independent signals.

## Ambiguity Handling
- Record unresolved ambiguity as first-class artifact.
- Allow multiple competing hypotheses when evidence conflicts.
- Defer resolution rather than forcing deterministic collapse.

## Conflict Handling
Conflicting evidence is represented explicitly with:
- competing relation assertions,
- evidence set per assertion,
- confidence per assertion (`confidence_score`, `confidence_band`),
- conflict status (`open|resolved|superseded`).

## Low-Confidence Handling Rule
If confidence remains `low`, Cortex must preserve unresolved state and must not emit deterministic-style conclusions.
