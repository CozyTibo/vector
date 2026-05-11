# Phase 01 Reconstruction Drill Checklist

Purpose: provide a repeatable operator checklist for Step 14 verification gate runs.

## Preconditions

- Tenant has at least one routed Cortex connector.
- Celery worker + Beat (or manual sync trigger path) are operational.
- Use admin verification endpoint:
  - `GET /admin/tenants/{tenant_id}/cortex/ingestion/verification?run_limit=30`

## Drill checklist

1. **Run + checkpoint integrity**
   - Latest run reports are parseable and run-level invariants pass.
   - Checkpoint timestamps parse.
2. **Health-row dominance guard**
   - `exhaust_depth.gate_checks` includes `ping_ratio_after_streams`.
   - Gate passes once non-health streams exist (ping ratio stays below threshold).
3. **Cross-connector evidence**
   - `multi_connector_non_health_evidence` passes for active tenants.
4. **Reconstruction signal coverage**
   - At least two categories show evidence in the gate:
     - conversational (`slack.message` / `calls.meeting` / `calls.transcript`)
     - planning (`linear.issue` / `notion.database_row` / `notion.page`)
     - delivery (`github.pull_request` / `github.commit` / `github.workflow_run` / `github.deployment`)
5. **Admin drilldown evidence**
   - `raw-stats` filtered by connector/resource/time confirms non-health rows and freshness.
   - Connector raw drilldown search finds representative payloads for at least two categories above.

## Exit signal (Step 14)

- Verification response `passed=true` with Step 14 gate enabled.
- `exhaust_depth.gate_passed=true`.
- Reconstruction checklist shows no missing mandatory evidence for the tenant being verified.

## Notes

- This checklist proves operational exhaust observability and verification behavior.
- Phase 01 still cannot close without Step 15 live-lane logical idempotency hardening.
