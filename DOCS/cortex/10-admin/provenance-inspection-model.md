# Provenance Inspection Model

## Objective
Allow operators to trace any phase object back to source raw evidence and forward to downstream artifacts.

## Lineage Views
- source lineage (raw refs),
- transformation lineage (phase transitions),
- replay lineage (replay job/version),
- AI inference lineage (if inference-assisted fields exist).

## Required Inspection Features
- chain navigation by `provenance.chain_id`,
- transformation-step timeline,
- version tuple visibility per step,
- unresolved lineage gap detection.

## Inspection Guarantees
- no object displayed without provenance.
- missing lineage triggers trust warning state.
