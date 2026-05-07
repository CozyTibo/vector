# Archival Strategy

## Archival Goals
- reduce hot storage pressure,
- preserve replay-accessible historical memory,
- maintain provenance and integrity guarantees.

## Archival Tiers
- hot tier: recent and frequently replayed windows.
- warm tier: less frequent but operationally relevant windows.
- cold tier: long-horizon history retained for replay/governance.

## Archival Rules
- moving payload to cold tier must not remove queryability of identity/provenance metadata.
- cold payload references require integrity hash and retrieval pointer.
- archival transitions are auditable events.

## Replay Rehydration
- replay scan identifies archived rows,
- payload retrieved via archival pointer,
- integrity hash verified before inclusion.

## Transcript-Specific Consideration
Large transcript payloads are primary archival candidates but must remain replay-hydratable without semantic loss.
