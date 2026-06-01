# Drift Detection Checklist

Use this checklist before approving architecture, schema, or phase-level changes.

## Terminology Drift
- [ ] New terms map to canonical ontology vocabulary.
- [ ] Deprecated/forbidden wording is not introduced.
- [ ] `project`, `initiative`, `thread`, `discussion`, `ownership`, `responsibility` are used consistently.
- [ ] Execution scope uses **Declared Domain** (V1) or **Emergent Domain** (future) — not `topic`, `topic materialization`, or `declared work rollup`.
- [ ] **Execution Surfaces** remain read-only consumers — no new passes, queues, or materialization tables in surface modules.

## Contract Drift
- [ ] Field names follow canonical naming conventions.
- [ ] Timestamp semantics (`occurred_at`, `observed_at`, `processed_at`, `inferred_at`) are preserved.
- [ ] Version fields (`schema_version`, `extraction_version`, `inference_version`, `replay_version`) remain explicit.
- [ ] Mutability rules are unchanged or explicitly revised with ADR.

## Provenance Drift
- [ ] `provenance.chain_id`, `provenance.input_refs`, and evidence refs remain present.
- [ ] New outputs preserve continuous lineage to raw evidence.
- [ ] No phase drops provenance on transformation.

## Confidence / AI Boundary Drift
- [ ] Confidence model remains `confidence_score` + `confidence_band`.
- [ ] Low confidence is represented as uncertainty, not forced resolution.
- [ ] AI usage remains bounded to ambiguity/synthesis/inference scopes.
- [ ] No AI pathway mutates canonical facts directly.

## Temporal Drift
- [ ] Validity windows (`effective_from`, `effective_to`) remain coherent.
- [ ] Supersession replaces overwrite semantics.
- [ ] Historical reconstruction logic is preserved across schema updates.

## Replay Drift
- [ ] Replay isolation assumptions remain valid.
- [ ] Replay metadata remains explicit (`replay_job_id`, `replay_version`).
- [ ] Replay determinism expectations are unchanged for deterministic stages.
- [ ] Replay does not require irreversible destructive operations.

## Phase Boundary Drift
- [ ] No responsibility leakage into non-owned phase logic.
- [ ] Connectors remain non-intelligent adapters.
- [ ] Retrieval does not perform synthesis.
- [ ] Synthesis does not mutate memory/canonical layers.

## Governance Decision
- [ ] If any item fails, block implementation until resolved.
- [ ] Record drift exceptions in ADR with mitigation plan.
