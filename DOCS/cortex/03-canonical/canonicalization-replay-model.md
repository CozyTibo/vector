# Canonicalization Replay Model

## Replay Objective
Regenerate canonical outputs from raw substrate with deterministic comparability.

## Replay Scope
- tenant + connector + time/object windows.
- optional ontology/mapping version migration scopes.

## Replay Behavior
- raw input remains immutable.
- canonical outputs may supersede prior outputs under new versions.
- replay divergence report required for trust decisions.

## Replay Safety
- replay cannot bypass provenance requirements.
- replay cannot force ambiguity resolution without evidence.
