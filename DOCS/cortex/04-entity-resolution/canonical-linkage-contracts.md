# Canonical Linkage Contracts

## Linkage Record Contract
Required fields:
- `tenant_id`
- `linkage_id`
- `linkage_type`
- `from_canonical_id`
- `to_canonical_id`
- `status`
- `confidence_score`
- `confidence_band`
- `provenance.chain_id`
- `supporting_evidence_refs[]`
- `effective_from`, `effective_to`
- `schema_version`
- `processor_version`
- `replay_version`

## Continuity Record Contract
Required fields:
- `continuity_id`
- `continuity_subject_type`
- `continuity_subject_ids[]`
- `continuity_state`
- `confidence_score`, `confidence_band`
- temporal validity fields
- provenance fields.

## Ambiguity Record Contract
Required fields:
- `ambiguity_id`
- `ambiguity_type`
- `candidate_refs[]`
- `ambiguity_reason`
- `confidence_score`, `confidence_band`
- `status`
- provenance + replay fields.
