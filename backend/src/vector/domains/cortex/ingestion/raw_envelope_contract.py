"""Phase 01 Step 4 — frozen-core raw payload checks before persistence.

Maps the doctrine in ``01-ingestion/raw-envelope-contract-stability.md`` onto the JSON
``payload_body`` we store on ``raw_ingestion_records`` (normalized connector snapshot rows).

Additive-only: unknown top-level keys are allowed. ``cortex_replay_metadata`` is validated
when present (Step 3 replay tagging).
"""

from __future__ import annotations

import uuid
from typing import Any

MAX_SUPPORTED_SCHEMA_VERSION = 1


class EnvelopeContractViolation(ValueError):
    """Raised when a raw row payload violates persistence contracts."""


def _require_int(name: str, value: object, *, minimum: int = 1, maximum: int | None = None) -> int:
    if type(value) is not int:
        raise EnvelopeContractViolation(f"{name} must be an int")
    if value < minimum:
        raise EnvelopeContractViolation(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise EnvelopeContractViolation(f"{name} must be <= {maximum}")
    return value


def _require_non_empty_str(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise EnvelopeContractViolation(f"{name} must be a string")
    s = value.strip()
    if not s:
        raise EnvelopeContractViolation(f"{name} must be non-empty")
    return s


def _validate_ingestion_version_tuple(value: object) -> None:
    if not isinstance(value, dict):
        raise EnvelopeContractViolation("ingestion_version must be an object when present")
    for k in ("schema_version", "extraction_version", "processor_version"):
        if k not in value:
            raise EnvelopeContractViolation(f"ingestion_version missing {k!r}")
        _require_int(f"ingestion_version.{k}", value[k], minimum=1)


def _validate_replay_metadata(value: object) -> None:
    if not isinstance(value, dict):
        raise EnvelopeContractViolation("cortex_replay_metadata must be an object when present")
    rid = value.get("replay_job_id")
    if not isinstance(rid, str) or not rid.strip():
        msg = "cortex_replay_metadata.replay_job_id must be a non-empty string"
        raise EnvelopeContractViolation(msg)
    try:
        uuid.UUID(rid.strip())
    except ValueError as e:
        msg = "cortex_replay_metadata.replay_job_id must be a UUID string"
        raise EnvelopeContractViolation(msg) from e
    _require_int("cortex_replay_metadata.replay_version", value.get("replay_version"), minimum=1)
    _require_non_empty_str("cortex_replay_metadata.sync_mode", value.get("sync_mode"))


def validate_raw_payload_for_persistence(
    *,
    connector: str,
    connection_id: uuid.UUID,
    body: dict[str, Any],
) -> None:
    """Validate ``body`` immediately before persisting a ``RawIngestionRecord``.

    Call after replay tagging so ``cortex_replay_metadata`` is visible when applicable.
    """
    sv = body.get("schema_version")
    sv_int = _require_int("schema_version", sv, minimum=1, maximum=MAX_SUPPORTED_SCHEMA_VERSION)

    ctype = _require_non_empty_str("connector_type", body.get("connector_type"))
    if ctype != connector:
        raise EnvelopeContractViolation(
            f"connector_type {ctype!r} does not match connection provider {connector!r}",
        )

    inst = _require_non_empty_str("connector_instance_id", body.get("connector_instance_id"))
    if inst != str(connection_id):
        raise EnvelopeContractViolation("connector_instance_id does not match connection_id")

    _require_non_empty_str("source_object_type", body.get("source_object_type"))
    if "source_object_id" not in body:
        raise EnvelopeContractViolation("source_object_id is required")
    soid = body["source_object_id"]
    if not isinstance(soid, str):
        raise EnvelopeContractViolation("source_object_id must be a string")

    if "ingestion_version" in body:
        _validate_ingestion_version_tuple(body["ingestion_version"])
    elif sv_int > 1:
        raise EnvelopeContractViolation("ingestion_version is required when schema_version > 1")

    if "cortex_replay_metadata" in body:
        _validate_replay_metadata(body["cortex_replay_metadata"])


def core_envelope_fields(
    *,
    connector: str,
    connection_id: uuid.UUID,
    source_object_type: str,
    source_object_id: str,
) -> dict[str, Any]:
    """Return required frozen-core keys plus pinned ``ingestion_version`` tuple (defaults v1)."""
    return {
        "schema_version": 1,
        "connector_type": connector,
        "connector_instance_id": str(connection_id),
        "source_object_type": source_object_type,
        "source_object_id": source_object_id,
        "ingestion_version": {
            "schema_version": 1,
            "extraction_version": 1,
            "processor_version": 1,
        },
    }
