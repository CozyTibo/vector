# Provenance Propagation

## Objective
Preserve reconstructable lineage from raw records to canonical outputs.

## Propagation Fields
- `provenance.chain_id`
- `provenance.input_refs`
- `provenance.source_refs`
- `provenance.transform_stage = canonical`
- `provenance.processor_version`
- `provenance.generated_at`
- replay context fields where applicable.

## Propagation Stages
1. ingest raw evidence refs,
2. attach transformation metadata per canonical output,
3. preserve ambiguity and confidence lineage for inferred fields.

## Continuity Rules
- no canonical object persists without provenance lineage.
- downstream phases can always trace canonical artifacts back to raw evidence.
