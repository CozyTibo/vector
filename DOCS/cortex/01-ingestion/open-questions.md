# 01-ingestion Open Questions

## Questions To Resolve
- How long can connector desync persist before hard-stop?
- What minimum source metadata is mandatory before accepting envelope?
- Should ingestion block on missing optional scopes or degrade mode?

## Blockers
- Connector auth model not finalized
- Envelope schema version not frozen

## Resolution Rule
All blockers must be cleared before implementation kickoff for this phase.
