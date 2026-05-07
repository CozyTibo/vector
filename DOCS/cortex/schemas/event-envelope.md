# Event Envelope Standard

## Raw Envelope Fields
- source system + connector identity
- source object type + object id
- event type and event timestamp
- payload hash for deduplication
- tenant id and ingestion run id
- fetch cursor/watermark metadata

## Canonical Envelope Fields
- canonical event id
- canonical type
- canonical entity references
- derived relation references
- transformation processor version
- confidence and ambiguity flags (if applicable)
