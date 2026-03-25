"""Explicit ordering for reprocessing append-only ingestion records.

All consumers that replay raw observations (projection rebuilds, normalization passes,
debug exports) MUST apply this ordering so behavior is deterministic across processes.

Rule
----
``ORDER BY replay_sequence ASC, id ASC``

- ``replay_sequence`` is assigned from PostgreSQL sequence ``raw_ingestion_replay_seq``
  at insert time (globally monotonic across connections).
- ``id`` is the table primary key (bigserial) and breaks ties if ever needed.

Do not use ``fetched_at`` alone as the primary replay key: concurrent inserts can share
the same timestamp; ``replay_sequence`` is the stable total order for persisted rows.
"""

REPLAY_ORDER_SQL = "replay_sequence ASC, id ASC"
