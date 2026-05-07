# AI Philosophy

## AI Role Envelope
AI is permitted for:
- ambiguity classification,
- semantic topic linking,
- concern and risk phrasing normalization,
- causal hypothesis proposal,
- bounded summarization.

AI is forbidden for:
- creating raw or canonical facts,
- rewriting deterministic identity mappings,
- deciding retention/deletion policy,
- silently resolving conflicting evidence.

## Invocation Preconditions
AI invocation requires:
1. Deterministic extraction already completed.
2. Explicit ambiguity marker in inputs.
3. Bounded evidence packet with provenance ids.
4. Target output schema with confidence fields.

## Output Semantics
AI outputs must contain:
- inference_type,
- confidence_score and confidence_band,
- supporting_evidence_refs,
- inference_version,
- inferred_at,
- replay_version.

## Failure Behavior
If confidence is below threshold, Cortex must emit unresolved ambiguity artifacts instead of coerced conclusions.
