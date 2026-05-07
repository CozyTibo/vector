# Connector State Schema

## Table: `connector_runtime_state`
Purpose: persistent operational state per tenant connector instance.

## Primary Scope
- unique (`tenant_id`, `connector_instance_id`)

## Fields
- static identity:
  - `tenant_id`, `connector_type`, `connector_instance_id`, `created_at`
- mutable operational state:
  - `enabled` (bool)
  - `state` (`READY`, `RUNNING`, `THROTTLED`, `DEGRADED`, `AUTH_FAILED`, `DISABLED`, `MAINTENANCE`, `REPLAYING`)
  - `last_successful_run_id`
  - `last_failed_run_id`
  - `last_heartbeat_at`
  - `sync_lag_seconds`
  - `auth_status` + `auth_last_validated_at`
  - `rate_limit_reset_at`, `rate_limit_budget_remaining`
  - `current_live_checkpoint_ref`
  - `current_replay_checkpoint_ref` (nullable)
  - `updated_at`

## Mutable vs Immutable
- immutable: identity fields.
- mutable: operational state and pointers.

## Transition Persistence
- every state transition should be audit-loggable (state change event).
- forbidden transitions enforced by state machine contract.

## Replay Interactions
- replay state and pointers are separate from live state pointers.
- replay state must not clear live lag metrics.
