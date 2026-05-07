# Extraction Strategy

## Deterministic Extraction (Required First Pass)
Deterministic extraction covers:
- source ids and stable references,
- timestamps and revision markers,
- URLs and explicit links,
- ticket/repo/user references,
- explicit mention and thread linkage,
- explicit state transitions.

## AI-Assisted Extraction (Ambiguity Boundaries)
AI-assisted extraction is limited to:
- semantic topic detection,
- concern detection and phrasing normalization,
- initiative clustering where explicit links are absent,
- ambiguous reference disambiguation,
- causal hypothesis generation,
- bounded summarization.

## Hybrid Workflow
1. Deterministic extraction first.
2. Mark unresolved ambiguity fields.
3. Invoke AI only on unresolved fields and bounded context packs.
4. Persist inference artifacts with confidence and evidence refs.
5. Never overwrite deterministic facts with AI output.
