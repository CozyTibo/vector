# Ingestion Depth Model (Maturity Levels)

Explicit maturity levels so we **never again conflate** “ingestion substrate exists” with “organizational exhaust is fully acquired.”

Levels apply **per connector** (overall level = minimum / declared policy — document which rule you use). Resource rows in `connector-exhaust-matrix.md` may trail the connector headline level.

## Level 0 — Connectivity only

OAuth / tokens valid; may have no durable raw exhaust beyond synthetic health rows.

## Level 1 — Ping / shallow fetch

Single-call or synthetic **scope ping** / **viewer ping** proving routing and credentials. **Not** organizational exhaust completeness.

## Level 2 — Incremental sync operational

At least one **non-trivial resource stream** is fetched with **checkpointed incremental** semantics (cursor / since / etag as applicable) and persisted as raw rows.

## Level 3 — Historical backfill operational

Defined **historical window** (or full-history policy) can be **backfilled** with resumable checkpoints and operator-visible progress / limits.

## Level 4 — Replay-safe deep ingestion

All **Level 2–3** streams that are marked “replay relevant” meet **replay isolation + idempotency** contracts for scoped replay jobs (see Phase 01 replay spec).

## Level 5 — Canonicalization-compatible completeness

Raw envelopes and resource coverage are **sufficient and stable** for Phase 03 mappers: identifiers, timestamps, parent/child links needed for canonical projection are present or explicitly modeled as gaps.

## Level 6 — Operationally trusted organizational exhaust

Production SLOs, monitoring, failure classes, cost controls, and operator runbooks exist for **this connector’s exhaust** at declared depth.

---

**Runtime alignment:** The internal admin **Cortex ingestion** page surfaces `maturity_level` and per-resource rows from the live registry (`GET …/cortex/ingestion/exhaust-coverage`) so docs and UI stay honest.
