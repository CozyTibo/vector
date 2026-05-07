# Incident Analysis Capability

Incident analysis reconstructs operational reality during failure periods.

## Reconstruction Scope

- rollout lineage,
- decision chain progression,
- blocker emergence timeline,
- ownership shifts during response,
- communication propagation,
- divergence between expected and actual execution.

## Evidence Reconstruction vs Speculative Causality

- **Evidence reconstruction:** sequence and linkage backed by observed data.
- **Speculative causality:** hypotheses about why events happened.

Cortex must keep these separate. Hypotheses can exist, but they must remain explicitly uncertain and evidence-scoped.

## Required Primitives

- high-fidelity event chronology,
- decision/action linkage,
- temporal diff tools,
- ambiguity/confidence display,
- replay comparison for post-incident reprocessing.

## Capability Risk

If timeline ordering or identity linkage is weak, incident narratives collapse into anecdotes.
