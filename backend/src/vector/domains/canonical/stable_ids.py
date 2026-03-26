"""Deterministic UUIDs for canonical entities (idempotent Step 3)."""

from __future__ import annotations

import uuid


def tenant_namespace(tenant_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"vector:tenant:{tenant_id}")


def external_reference_uuid(tenant_id: uuid.UUID, connector: str, external_key: str) -> uuid.UUID:
    return uuid.uuid5(
        tenant_namespace(tenant_id),
        f"external_reference:{connector}:{external_key}",
    )


def artifact_uuid(tenant_id: uuid.UUID, connector: str, external_key: str) -> uuid.UUID:
    return uuid.uuid5(
        tenant_namespace(tenant_id),
        f"artifact:{connector}:{external_key}",
    )


def actor_uuid(tenant_id: uuid.UUID, connector: str, external_key: str) -> uuid.UUID:
    return uuid.uuid5(
        tenant_namespace(tenant_id),
        f"actor:{connector}:{external_key}",
    )


def relationship_uuid(
    tenant_id: uuid.UUID,
    *,
    subject_type: str,
    subject_id: uuid.UUID,
    object_type: str,
    object_id: uuid.UUID,
    relation_kind_id: int,
    valid_from_key: str,
) -> uuid.UUID:
    return uuid.uuid5(
        tenant_namespace(tenant_id),
        "relationship:"
        f"{subject_type}:{subject_id}:"
        f"{object_type}:{object_id}:"
        f"rk:{relation_kind_id}:vf:{valid_from_key}",
    )
