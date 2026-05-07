# Connector Philosophy

## Connector Responsibility
Connectors are source adapters. They authenticate, fetch, paginate, normalize source envelopes, and expose source metadata.

## Connector Non-Responsibility
Connectors must never perform:
- organizational reasoning,
- cross-tool identity resolution,
- graph inference,
- causal interpretation.

## Connector Contract
Each connector should define:
- auth models and token lifecycle handling,
- initial backfill strategy,
- incremental sync and watermarking,
- rate-limit and retry behavior,
- idempotent source event identifiers,
- webhook/realtime extension path.

## Depth Requirement
Each connector roadmap must include maximum useful organizational data depth, not only minimal MVP fields.
