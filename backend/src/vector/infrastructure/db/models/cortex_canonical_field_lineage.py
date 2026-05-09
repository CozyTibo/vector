"""Per-field lineage rows for transform provenance (`phase-03-transform-lineage-doctrine.md`)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
        CortexCanonicalTransformMaterialization,
    )


class CortexCanonicalFieldLineage(Base):
    __tablename__ = "cortex_canonical_field_lineage"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    materialization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_transform_materializations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_path: Mapped[str] = mapped_column(String(512), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(256), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(8), nullable=False)
    confidence_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    source_paths: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False)
    value_snapshot: Mapped[Any] = mapped_column(JSONB(), nullable=True)

    materialization: Mapped[CortexCanonicalTransformMaterialization] = relationship(
        back_populates="field_lineage",
    )
