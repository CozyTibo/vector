# Raw Memory Versioning

## Version Dimensions
- source API version,
- source revision/version marker,
- ingestion schema version,
- extraction version,
- processor version,
- replay version context.

## Immutable vs Versioned
- immutable:
  - raw payload for a row,
  - source identity for a row,
  - source chronology for a row.
- versioned metadata:
  - ingestion/replay context,
  - retrieval and rehydration location metadata.

## Lineage Requirement
Version metadata must allow auditors to answer:
- which extractor/parser version saw this payload,
- which replay context consumed this payload,
- how historical versions differ without mutating raw evidence.
