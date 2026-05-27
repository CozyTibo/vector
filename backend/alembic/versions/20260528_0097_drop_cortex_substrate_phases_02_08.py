"""Drop unused Cortex substrate tables (phases 02–08 pipeline; ingestion retained).

Revision ID: 20260528_0097
Revises: 20260527_0096

Removes ORM-backed tables for deleted substrate execution (canonical → synthesis).
Keeps: ingestion + raw_memory_* + connector tables + phase-09 admin snapshot tables.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260528_0097"
down_revision: Union[str, None] = "20260527_0096"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Child tables first; each DROP uses CASCADE for leftover FKs between listed tables.
# Does not cascade to raw_ingestion_records / tenants.
_DROP_ORDER: tuple[str, ...] = (
    # Phase 08 — synthesis
    "cortex_synthesis_job_receipts",
    "cortex_synthesis_artifacts",
    "cortex_synthesis_retention_events",
    "cortex_synthesis_publication_epochs",
    "cortex_synthesis_certification_archives",
    "cortex_synthesis_activation_audits",
    "cortex_synthesis_jobs",
    # Phase 07 — retrieval
    "cortex_retrieval_index_entries",
    "cortex_retrieval_query_audit",
    "cortex_retrieval_materialization_reports",
    "cortex_retrieval_index_epochs",
    # Phase 06 — TCRE / artifact lineage
    "cortex_tcre_reconstruction_artifacts",
    "cortex_tcre_reconstruction_jobs",
    "cortex_artifact_lineage_edges",
    # Phase 05 — graph traversal (OCTS)
    "cortex_octs_traversal_receipts",
    "cortex_octs_traversal_replay_archive",
    "cortex_octs_durable_walk_records",
    # Phase 04 — org / identity graph
    "cortex_org_link_replay_job_receipts",
    "cortex_org_link_replay_jobs",
    "cortex_org_link_candidates",
    "cortex_org_links",
    "cortex_org_primitive_instances",
    "cortex_org_merges",
    "cortex_org_ambiguity_records",
    "cortex_org_remediation_validations",
    "cortex_org_failure_cases",
    "cortex_org_verification_runs",
    "cortex_org_identity_console_audits",
    "cortex_org_identity_backfill_runs",
    "cortex_org_certification_archives",
    "cortex_org_entities",
    "cortex_org_link_candidate_batches",
    "cortex_org_link_promotion_policies",
    "cortex_org_merge_policies",
    "cortex_link_rule_versions",
    "cortex_bundle_equivalence_declarations",
    # Phase 03 — canonical + mapping bundles
    "cortex_canonical_field_lineage",
    "cortex_canonical_provenance_records",
    "cortex_canonical_ambiguity_lifecycle_events",
    "cortex_canonical_replay_job_receipts",
    "cortex_canonical_identity_anchors",
    "cortex_canonical_temporal_supersessions",
    "cortex_canonical_ambiguity_records",
    "cortex_canonical_remediation_validations",
    "cortex_canonical_failure_cases",
    "cortex_canonical_verification_runs",
    "cortex_canonical_stabilization_proof_runs",
    "cortex_canonical_certification_archives",
    "cortex_canonical_replay_jobs",
    "cortex_canonical_materialization_deferrals",
    "cortex_canonical_transform_materializations",
    "cortex_mapping_bundle_pins",
    "cortex_mapping_bundle_changelog",
    "cortex_mapping_bundle_compatibility",
    "cortex_mapping_bundles",
    # Pipeline / execution orchestration (substrate coordinator removed from code)
    "cortex_substrate_phase_runs",
    "cortex_substrate_pipeline_dead_letters",
    "cortex_pipeline_continuation_states",
    "cortex_execution_transition_log",
    "cortex_execution_island_registry",
    "cortex_tenant_convergence_leases",
    "cortex_identity_celery_dispatches",
    "cortex_replay_divergence_events",
    "cortex_replay_storm_controls",
    "cortex_substrate_pipeline_runs",
)

# Phase 09 admin snapshots intentionally retained:
# cortex_admin_continuity_snapshot, cortex_admin_graph_component_snapshot,
# cortex_phase09_readiness_signoffs


def upgrade() -> None:
    for table in _DROP_ORDER:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible: Cortex substrate phase 02–08 tables were dropped. Restore from backup if needed."
    )
