# 02-raw-store Open Questions

## Questions To Resolve
- What is minimum replay checkpoint interval?
- How will legal deletion requests preserve replay auditability?
- What payload hashing strategy prevents collisions operationally?

## Blockers
- Append-only write protections undefined
- Retention + deletion semantics unresolved

## Resolution Rule
All blockers must be cleared before implementation kickoff for this phase.
