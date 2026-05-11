# Phase 02 Ambiguity Audit

## Objective
Remove wording that can cause implementation drift or implicit overclaims.

## Audited Terms and Required Interpretation

| Term | Approved Meaning in Phase 02 | Disallowed Interpretation |
| ---- | ---------------------------- | ------------------------- |
| memory | preserved raw evidence continuity | semantic organizational memory/intelligence |
| reconstruction | preserved observed evidence retrieval | perfect objective historical truth |
| truth | chain-of-observation trust | semantic/causal correctness |
| replay-safe | deterministic isolated replay over preserved evidence | replay-complete omniscience |
| durable | persistence under declared retention/archival constraints | infinite undeletable history |
| preserved | captured and retained per policy | provider-global completeness |
| continuity | lineage/revision/provenance continuity in preserved scope | guarantee of no unobserved gaps |
| historical | as-of preserved timeline semantics | full provider past reconstruction |

## Fixed Ambiguity Classes
- replay omniscience implication: fixed with replay-safe vs replay-complete doctrine.
- reconstruction overclaim: fixed with preserved-observation semantics and gap classes.
- health theater language: fixed with explicit trust-state taxonomy.
- semantic leakage in query/admin: fixed with anti-goal guardrails.

## Remaining Ambiguities To Close Before Runtime
- threshold values for trust-state transitions and closure gate tolerances,
- exact API schema for trust-state annotations on retrieval responses,
- canonical representation of continuity-gap markers in runtime payloads.
