# Canonicalization Cost Model

## Cost Drivers
- deterministic extraction compute volume,
- AI-assisted extraction invocation rate,
- ontology mapping complexity,
- ambiguity registration volume,
- replay/reprocessing frequency.

## Replay/Reprocessing Cost
- major contributor when version upgrades require broad historical reruns.
- bounded by scope selection, lane prioritization, and replay scheduling.

## Ontology Expansion Cost
- new ontology concepts increase mapping maintenance and replay coverage needs.

## Cost Guardrails
- prefer deterministic extraction where sufficient.
- keep AI invocation bounded to ambiguity boundaries.
- monitor ambiguity volume as potential cost amplifier.
