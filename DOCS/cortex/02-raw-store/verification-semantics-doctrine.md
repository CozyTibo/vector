# Phase 02 Verification Semantics Doctrine

## Purpose
Define one authoritative verification truth model for Phase 02 runtime and admin surfaces.

## Canonical Verification Path (Step 12 target)
All Phase 02 surfaces must derive from a shared gate computation path:
- aggregate verification endpoint,
- trust-state annotation derivation,
- control-plane verification summary,
- phase-closure evaluator.

No surface may compute a divergent pass/fail result from a different gate precedence model.

## Required Semantics
- deterministic gate ordering and precedence,
- consistent hard/soft/warn interpretation,
- aligned closure and trust-state semantics,
- explicit freshness metadata for verification snapshots,
- explicit proof-quality annotation (`measured`, `inferred`, `stale`, `partial`, `unverifiable`).

## Split-Brain Prevention
The following are prohibited:
- duplicated gate logic with different pass/fail behavior,
- closure status that contradicts trust-state source verification,
- control-plane summaries that omit blocking evidence from canonical verification state.

## Enforcement Readiness
Verification must also emit calibrated enforcement outputs:
- `would_block` decisions for non-catastrophic states,
- `blocked` decisions for catastrophic states,
- deterministic reason codes that match trust-state transitions.
