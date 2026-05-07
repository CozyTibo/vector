# Cross-Tool Identity Model

## Objective
Resolve identity across tool-specific representations without forcing unsafe merges.

## Example Cross-Tool Surfaces
- Slack user <-> GitHub user <-> Linear user,
- discussion threads <-> issues <-> PRs <-> docs,
- initiatives <-> channels <-> repositories.

## Deterministic Cross-Tool Signals
- exact external ids,
- verified email/account mapping (when policy allows),
- explicit cross-links and source references,
- stable source identity tuples.

## Probabilistic/AI-Assisted Signals
- semantic context overlap,
- participation and timeline correlation,
- weak naming similarity with evidence constraints.

## Conflict/Unresolved Handling
- conflicting candidates remain explicit,
- unresolved links are first-class records,
- temporal drift (renames/reassignments) captured via validity windows.
