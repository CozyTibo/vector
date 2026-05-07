# AI-Assisted Extraction Model

## Allowed AI Scope
AI may assist with:
- implicit topic extraction,
- semantic linkage hypotheses,
- ambiguity classification,
- concern/initiative clustering cues,
- non-authoritative candidate decision/action interpretation.

## Forbidden AI Scope
- cannot mutate raw truth,
- cannot overwrite deterministic extracted facts,
- cannot invent provenance,
- cannot emit strategic reasoning conclusions,
- cannot bypass ontology constraints.

## Invocation Preconditions
- deterministic extraction completed first.
- ambiguity boundary explicitly identified.
- bounded evidence packet with source refs supplied.

## Output Obligations
- `inference_type`
- `confidence_score`, `confidence_band`
- `ambiguity_reason` when unresolved
- `supporting_evidence_refs`
- `inference_version`, `inferred_at`, `replay_version`

## Replay/Versioning
- AI-assisted outputs are replay-sensitive and must be version-pinned.
- replay comparisons must distinguish expected model-version divergence from anomalies.
