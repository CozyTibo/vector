# Ontology Mapping Strategy

## Mapping Objective
Convert source-native object/event shapes into canonical ontology concepts with deterministic-first rules.

## Mapping Rules
- explicit mapping registry per connector object/event type.
- mapping outputs constrained to approved ontology concepts.
- unknown mappings produce unresolved mapping records, not silent fallback.

## Example Mappings
- Slack thread -> canonical `Thread` + `Discussion` events.
- GitHub PR -> canonical `Artifact` + action/event stream.
- Linear issue -> canonical work `Artifact` + ownership/dependency relations.
- Notion decision page -> canonical `Decision` candidate with provenance.

## Ambiguous Mapping Handling
- multiple candidate mappings allowed with confidence bands.
- conflicting mappings remain explicit until resolution policy applies.

## Multi-Source Mapping
- same organizational concept across tools maps via shared canonical identity references.
- no forced merge at canonicalization stage beyond deterministic evidence.

## Ontology Evolution
- mapping registry is versioned.
- mapping changes require replay plan and compatibility notes.
