# Deterministic Extraction Model

## Deterministic-Only Scope
Must remain deterministic:
- explicit IDs and object references,
- explicit timestamps and revisions,
- explicit URLs and cross-links,
- explicit mentions and assignments,
- explicit repo/ticket/doc references,
- explicit state transitions and status markers.

## Deterministic Pipeline Behavior
- no probabilistic interpretation in this stage.
- same raw input + version context yields same extracted fields.

## Error Behavior
- malformed deterministic fields produce structured extraction errors.
- deterministic failures do not trigger automatic AI fallback without ambiguity classification.

## Replay Implications
- deterministic extraction is replay baseline for canonical reproducibility.
