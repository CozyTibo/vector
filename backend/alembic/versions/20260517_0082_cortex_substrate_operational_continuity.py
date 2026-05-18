"""Cortex substrate operational continuity — continuation, retrieval diagnostics, synthesis audits.

Revision ID: 20260517_0082
Revises: 20260517_0081
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260517_0082"
down_revision: Union[str, None] = "20260517_0081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_pipeline_continuation_states",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("substrate_pipeline_run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("current_phase", sa.String(length=64), nullable=False),
        sa.Column("waiting_on", sa.String(length=64), nullable=True),
        sa.Column("async_job_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("async_job_type", sa.String(length=64), nullable=True),
        sa.Column("continuation_status", sa.String(length=32), nullable=False),
        sa.Column("continuation_nonce", sa.String(length=64), nullable=False),
        sa.Column("resume_identity_digest", sa.String(length=128), nullable=True),
        sa.Column("resume_receipt_hash", sa.String(length=128), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recovery_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "detail_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["substrate_pipeline_run_id"],
            ["cortex_substrate_pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "substrate_pipeline_run_id",
            name="uq_cortex_pipeline_continuation_pipeline_run",
        ),
    )
    op.create_index(
        "ix_cortex_pipeline_continuation_tenant_status",
        "cortex_pipeline_continuation_states",
        ["tenant_id", "continuation_status"],
    )
    op.create_index(
        "ix_cortex_pipeline_continuation_waiting_heartbeat",
        "cortex_pipeline_continuation_states",
        ["waiting_on", "last_heartbeat_at"],
    )

    op.create_table(
        "cortex_retrieval_materialization_reports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("retrieval_epoch", sa.String(length=128), nullable=True),
        sa.Column("tcre_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("walks_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("org_link_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "skip_reasons_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "report_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["cortex_substrate_pipeline_runs.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cortex_retrieval_mat_report_tenant_created",
        "cortex_retrieval_materialization_reports",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "cortex_synthesis_activation_audits",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("scopes_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scopes_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("workloads_applied", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synthesis_jobs_enqueued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synthesis_jobs_started", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synthesis_jobs_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("empty_scope_reason", sa.String(length=128), nullable=True),
        sa.Column(
            "audit_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["cortex_substrate_pipeline_runs.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cortex_synthesis_activation_audit_tenant_created",
        "cortex_synthesis_activation_audits",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("cortex_synthesis_activation_audits")
    op.drop_table("cortex_retrieval_materialization_reports")
    op.drop_table("cortex_pipeline_continuation_states")
