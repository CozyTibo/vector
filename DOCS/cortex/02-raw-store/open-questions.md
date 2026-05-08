# 02-raw-store Open Questions

## Questions To Resolve
- What is minimum replay checkpoint interval?
- How will legal deletion requests preserve replay auditability?
- What payload hashing strategy prevents collisions operationally?
- What trust-state threshold values determine healthy vs degraded vs unverifiable?
- What binary closure gate tolerances are required for final Phase 02 closure?
- What API shape carries continuity-gap/reconstruction-limited annotations?

## Blockers
- Append-only write protections undefined
- Retention + deletion semantics unresolved
- Trust-state threshold calibration unresolved
- Binary closure gate tolerances unresolved

## Resolution Rule
All blockers must be cleared before implementation kickoff for this phase.
