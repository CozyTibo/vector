# Cortex ingestion-only — database cleanup tracker

**Status:** Code removed (substrate phases 02–08). **No migrations applied yet** — tables and ORM models remain until a dedicated drop migration.

## Keep (ingestion + raw store + connectors)

| Table | Model |
|-------|--------|
| `raw_ingestion_records` | `raw_ingestion_record.RawIngestionRecord` |
| `ingestion_runs` | `ingestion_run.IngestionRun` |
| `connector_sync_state` | `connector_sync_state.ConnectorSyncState` |
| `raw_memory_lineage_index` | `raw_memory_lineage_index.RawMemoryLineageIndex` |
| `raw_memory_revision_index` | `raw_memory_revision_index.RawMemoryRevisionIndex` |
| `raw_memory_archive_catalog` | `raw_memory_archive_catalog.RawMemoryArchiveCatalog` |
| `raw_memory_retention_events` | `raw_memory_retention_event.RawMemoryRetentionEvent` |
| `raw_memory_trust_state` | `raw_memory_trust_state.RawMemoryTrustState` |
| `raw_memory_trust_transitions` | `raw_memory_trust_transition.RawMemoryTrustTransition` |
| `raw_memory_failure_cases` | `raw_memory_failure_case.RawMemoryFailureCase` |
| `raw_memory_recovery_validations` | `raw_memory_recovery_validation.RawMemoryRecoveryValidation` |

**Connector plumbing (non-`cortex_` prefix):** `tenant_connections`, provider detail tables (`slack_connection_details`, `github_connection_details`, `linear_connection_details`, `notion_connection_details`, `calls_connection_details`, etc.) — keep.

**Fields on kept tables (review only, do not drop with table):**

- `raw_ingestion_records.replay_job_id`, `replay_version` — ingestion replay lane
- `ingestion_runs.replay_mode`, `replay_job_id`, `replay_version`, `sync_mode`, `stats`, etc.

## Drop — substrate pipeline & execution (phase 02–08 orchestration)

| Table | Former phase |
|-------|----------------|
| `cortex_substrate_pipeline_runs` | pipeline |
| `cortex_substrate_phase_runs` | pipeline |
| `cortex_substrate_pipeline_dead_letters` | pipeline |
| `cortex_pipeline_continuation_states` | pipeline |
| `cortex_tenant_convergence_leases` | execution |
| `cortex_execution_transition_log` | execution |
| `cortex_execution_island_registry` | execution |
| `cortex_identity_celery_dispatches` | identity jobs |
| `cortex_admin_continuity_snapshot` | admin operator |
| `cortex_admin_graph_component_snapshot` | admin operator |
| `cortex_phase09_readiness_signoffs` | operational |
| `cortex_replay_storm_controls` | operational |
| `cortex_replay_divergence_events` | operational |

## Drop — canonical (substrate `phase_02_canonical`)

| Table |
|-------|
| `cortex_canonical_transform_materializations` |
| `cortex_canonical_provenance_records` |
| `cortex_canonical_identity_anchors` |
| `cortex_canonical_field_lineage` |
| `cortex_canonical_temporal_supersessions` |
| `cortex_canonical_ambiguity_records` |
| `cortex_canonical_ambiguity_lifecycle_events` |
| `cortex_canonical_failure_cases` |
| `cortex_canonical_verification_runs` |
| `cortex_canonical_remediation_validations` |
| `cortex_canonical_replay_jobs` |
| `cortex_canonical_replay_job_receipts` |
| `cortex_canonical_stabilization_proof_runs` |
| `cortex_canonical_certification_archives` |
| `cortex_canonical_materialization_deferrals` |
| `cortex_mapping_bundles` |
| `cortex_mapping_bundle_pins` |
| `cortex_mapping_bundle_changelog` |
| `cortex_mapping_bundle_compatibility` |
| `cortex_bundle_equivalence_declarations` |

**FK note:** Several canonical tables reference `raw_ingestion_records.id`. Drop child tables before altering raw FKs, or use `CASCADE` in migration.

## Drop — identity (substrate `phase_03_identity` / `phase_04_graph`)

| Table |
|-------|
| `cortex_org_entities` |
| `cortex_org_links` |
| `cortex_org_link_candidates` |
| `cortex_org_link_candidate_batches` |
| `cortex_org_link_promotion_policies` |
| `cortex_org_link_replay_jobs` |
| `cortex_org_link_replay_job_receipts` |
| `cortex_org_merges` |
| `cortex_org_merge_policies` |
| `cortex_org_primitive_instances` |
| `cortex_org_ambiguity_records` |
| `cortex_org_failure_cases` |
| `cortex_org_verification_runs` |
| `cortex_org_remediation_validations` |
| `cortex_org_identity_backfill_runs` |
| `cortex_org_identity_console_audits` |
| `cortex_org_certification_archives` |
| `cortex_link_rule_versions` |

## Drop — traversal (substrate `phase_05_traversal`)

| Table |
|-------|
| `cortex_octs_durable_walk_records` |
| `cortex_octs_traversal_receipts` |
| `cortex_octs_traversal_replay_archive` |

## Drop — TCRE / reasoning (substrate `phase_06_tcre`)

| Table |
|-------|
| `cortex_tcre_reconstruction_jobs` |
| `cortex_tcre_reconstruction_artifacts` |
| `cortex_artifact_lineage_edges` |

## Drop — retrieval (substrate `phase_07_retrieval`)

| Table |
|-------|
| `cortex_retrieval_index_epochs` |
| `cortex_retrieval_index_entries` |
| `cortex_retrieval_query_audit` |
| `cortex_retrieval_materialization_reports` |

## Drop — synthesis (substrate `phase_08_synthesis`)

| Table |
|-------|
| `cortex_synthesis_jobs` |
| `cortex_synthesis_job_receipts` |
| `cortex_synthesis_artifacts` |
| `cortex_synthesis_publication_epochs` |
| `cortex_synthesis_certification_archives` |
| `cortex_synthesis_retention_events` |
| `cortex_synthesis_activation_audits` |

## ORM cleanup (after migration)

Remove model modules under `backend/src/vector/infrastructure/db/models/cortex_*.py` except none of the above — all `cortex_*` models are in the drop list. Update `models/__init__.py` exports accordingly.

## Settings / Redis (no DB)

- `CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED` — harmless; dispatch is a no-op
- Remove beat keys for `vector.cortex.convergence.sweep` and `vector.cortex.admin.refresh_continuity_snapshots_sweep` from deployed workers (code already removed)

## Suggested migration order

1. Stop workers running old convergence/synthesis tasks.
2. Drop FK-dependent tables: canonical → identity → traversal → tcre → retrieval → synthesis → pipeline/execution.
3. Drop indexes and tables in reverse dependency order.
4. Remove SQLAlchemy models and alembic revision.
