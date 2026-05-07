# Initiative Continuity Capability

Initiative continuity preserves initiative identity and trajectory across tools, teams, and time.

## Core Needs

- detect initiative aliases/renames,
- preserve continuity through split/merge events,
- track ownership and dependency topology shifts,
- maintain continuity through connector and schema evolution.

## Required Primitives

- initiative identity resolution,
- lifecycle ontology (start/split/merge/retire),
- temporal continuity graph,
- replay-safe continuity reassignment rules.

## Typical Failure Modes

- initiative fragmentation into unrelated nodes,
- false merges of similar names,
- continuity loss after replay/version changes.
