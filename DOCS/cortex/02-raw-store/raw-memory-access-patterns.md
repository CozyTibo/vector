# Raw Memory Access Patterns

## Access Classes
| Class | Examples | Operational Priority |
| ----- | -------- | -------------------- |
| Replay-critical | Scoped replay retrieval for trust restoration | Highest |
| Incident forensics | Source-object and timeline drills | High |
| Integrity operations | Corruption/hash/provenance checks | High |
| Historical audit | Long-window governance exports | Medium |

## Hot Access Patterns
- replay scans for recent bounded windows,
- tenant + connector forensic lookups,
- source-object drilldowns for incident and defect analysis,
- integrity checks keyed by metadata before payload hydration.

## Cold Access Patterns
- long-horizon replay reconstruction,
- historical incident forensics,
- audit exports from archival windows.

## Access Constraints
- raw access is source-oriented and metadata-driven,
- semantic interpretation stays out of raw layer,
- archived access can be slower but must remain deterministic and complete.

## Ergonomics Guardrails
- enforce bounded windows in default operator workflows,
- require explicit escalation for unbounded history scans,
- default to metadata-first responses with optional payload expansion.
