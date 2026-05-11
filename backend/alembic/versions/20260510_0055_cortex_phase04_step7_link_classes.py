"""Cortex Phase 04 Step 7 — link_class (hint / inferred / prohibited) + authority CHECK.

Revision ID: 20260510_0055
Revises: 20260509_0054
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0055"
down_revision: Union[str, None] = "20260509_0054"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_org_links",
        sa.Column(
            "link_class",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'authoritative'"),
        ),
    )
    op.create_index(
        "ix_cortex_org_links_tenant_link_class",
        "cortex_org_links",
        ["tenant_id", "link_class"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_cortex_org_links_link_class_allowed",
        "cortex_org_links",
        "link_class IN ('authoritative', 'hint', 'inferred', 'prohibited')",
    )
    op.create_check_constraint(
        "ck_cortex_org_links_non_truth_authority",
        "cortex_org_links",
        "(link_class IN ('hint', 'inferred', 'prohibited') AND link_authority = 'non_authoritative') "
        "OR (link_class = 'authoritative' AND link_authority IN ('authoritative', 'candidate'))",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cortex_org_links_non_truth_authority", "cortex_org_links", type_="check")
    op.drop_constraint("ck_cortex_org_links_link_class_allowed", "cortex_org_links", type_="check")
    op.drop_index("ix_cortex_org_links_tenant_link_class", table_name="cortex_org_links")
    op.drop_column("cortex_org_links", "link_class")
