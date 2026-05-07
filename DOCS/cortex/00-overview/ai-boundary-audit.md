# AI Boundary Consistency Audit

## Allowed AI Domains (System-Wide)
- Ambiguity resolution after deterministic extraction.
- Semantic linking where explicit deterministic links are insufficient.
- Bounded summarization and synthesis phrasing.
- Causal hypothesis generation with confidence + evidence requirements.

## Forbidden AI Domains (System-Wide)
- Raw fact creation or mutation.
- Canonical identity truth assignment without deterministic evidence path.
- Connector-side organizational reasoning.
- Policy/governance decisions (retention, deletion, access).
- Silent conflict resolution without explicit uncertainty.

## Contract Requirements For AI Outputs
- `inference_type`
- `inference_version`
- `inferred_at`
- `confidence_score`
- `confidence_band`
- `supporting_evidence_refs`
- `ambiguity_reason` (when confidence is not high)
- `replay_version`

## Consistency Verdict (Current Pass)
- AI role is consistently constrained to ambiguity/synthesis/inference contexts.
- No documentation asserts AI-first extraction or AI-owned truth.
- Confidence and provenance requirements are aligned across schema and overview docs.
