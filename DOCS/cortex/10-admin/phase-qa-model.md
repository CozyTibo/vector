# Phase QA Model

## QA Purpose
Verify phase outputs are operationally trustworthy, replay-consistent, and provenance-complete.

## QA Dimensions
- replay equivalence,
- output completeness,
- provenance continuity,
- confidence and ambiguity sanity,
- ontology/mapping correctness (canonical phase),
- corruption absence.

## Healthy Output Criteria
- no critical invariant violations,
- bounded failure rates within SLO,
- unresolved ambiguity within expected ranges,
- replay divergence explainable by approved version changes.

## QA Artifacts
- phase QA report per release window,
- exception list with owner and remediation plan,
- trust status per phase (`trusted`, `conditional`, `untrusted`).
