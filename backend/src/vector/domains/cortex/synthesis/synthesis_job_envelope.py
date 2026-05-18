"""Phase 08 P08-06 — ``SynthesisJobEnvelopeV1`` normalization and envelope digest law."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.anti_goals import (
    enforce_synthesis_job_envelope_anti_goals_v1,
    validate_synthesis_authoritative_job_envelope_algebra_v1,
)
from vector.domains.cortex.synthesis.synthesis_bounded_caps import apply_synthesis_policy_pack_caps_v1
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
    enforce_synthesis_job_workload_and_intent_v1,
    resolve_synthesis_workload_and_intent_v1,
    validate_synthesis_job_envelope_schema_version_v1,
)

PHASE08_SYNTHESIS_JOB_ENVELOPE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_EXECUTION_PARTITIONS_V1: Final[frozenset[str]] = frozenset({"authoritative", "exploration"})


class SynthesisJobEnvelopeError(ValueError):
    """Raised when a synthesis job envelope fails validation."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def _parse_tenant_id(raw: object) -> uuid.UUID:
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError) as exc:
        raise SynthesisJobEnvelopeError(
            "invalid_tenant_id",
            detail={"tenant_id": raw},
        ) from exc


def synthesis_policy_pack_digest_v1(*, policy_pack_id: str | None = None) -> str:
    """Pinned digest for default synthesis policy pack (fixture id until pack loader ships)."""
    pack_id = policy_pack_id or DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1
    return hash_reasoning_canonical_json_sha256_v1(
        {"synthesis_policy_pack_id": pack_id, "schema_version": 1},
    )


def normalize_synthesis_job_envelope_v1(
    body: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Validate and normalize ``SynthesisJobEnvelopeV1`` (data contracts §3)."""
    validate_synthesis_job_envelope_schema_version_v1(body)
    partition_preview = str(body.get("execution_partition") or "authoritative").strip().lower()
    if partition_preview not in _EXECUTION_PARTITIONS_V1:
        raise SynthesisJobEnvelopeError(
            "invalid_execution_partition",
            detail={"execution_partition": partition_preview},
        )
    enforce_synthesis_job_envelope_anti_goals_v1(body)
    validate_synthesis_authoritative_job_envelope_algebra_v1(
        body,
        execution_partition=partition_preview,
    )
    env_tenant = _parse_tenant_id(body.get("tenant_id"))
    if env_tenant != tenant_id:
        raise SynthesisJobEnvelopeError(
            "tenant_id_scope_mismatch",
            detail={"envelope_tenant_id": str(env_tenant), "auth_tenant_id": str(tenant_id)},
        )
    wl, it = enforce_synthesis_job_workload_and_intent_v1(body)
    partition = str(body.get("execution_partition") or "authoritative").strip().lower()
    if partition not in _EXECUTION_PARTITIONS_V1:
        raise SynthesisJobEnvelopeError(
            "invalid_execution_partition",
            detail={"execution_partition": partition},
        )
    retrieval_scope = body.get("retrieval_scope")
    if retrieval_scope is not None and not isinstance(retrieval_scope, dict):
        raise SynthesisJobEnvelopeError("invalid_retrieval_scope")
    retrieval_pins = body.get("retrieval_pins")
    if retrieval_pins is not None and not isinstance(retrieval_pins, dict):
        raise SynthesisJobEnvelopeError("invalid_retrieval_pins")
    selection_policy = body.get("selection_policy")
    if selection_policy is not None and not isinstance(selection_policy, dict):
        raise SynthesisJobEnvelopeError("invalid_selection_policy")
    policy_pack_id = str(body.get("synthesis_policy_pack_id") or DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1)
    pack = load_synthesis_policy_pack_v1(policy_pack_id=policy_pack_id)
    caps = apply_synthesis_policy_pack_caps_v1(
        wl,
        selection_policy if isinstance(selection_policy, dict) else None,
        pack=pack,
    )
    if isinstance(selection_policy, dict):
        raw_simulate = selection_policy.get("llm_simulate")
        if isinstance(raw_simulate, str) and raw_simulate.strip():
            caps["llm_simulate"] = raw_simulate.strip()
    idempotency_key = body.get("idempotency_key")
    if idempotency_key is not None and not str(idempotency_key).strip():
        raise SynthesisJobEnvelopeError("invalid_idempotency_key")
    substrate_pipeline_run_id = body.get("substrate_pipeline_run_id")
    if substrate_pipeline_run_id is not None:
        try:
            uuid.UUID(str(substrate_pipeline_run_id))
        except ValueError as exc:
            raise SynthesisJobEnvelopeError(
                "invalid_substrate_pipeline_run_id",
                detail={"substrate_pipeline_run_id": substrate_pipeline_run_id},
            ) from exc
    pinned = body.get("pinned_retrieval_receipt")
    if pinned is not None and not isinstance(pinned, dict):
        raise SynthesisJobEnvelopeError("invalid_pinned_retrieval_receipt")
    replay_pins = body.get("replay_pins")
    if replay_pins is not None and not isinstance(replay_pins, dict):
        raise SynthesisJobEnvelopeError("invalid_replay_pins")
    policy_pack_digest = synthesis_policy_pack_digest_v1(policy_pack_id=policy_pack_id)
    envelope: dict[str, Any] = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": wl,
        "synthesis_intent": it,
        "execution_partition": partition,
        "retrieval_scope": dict(retrieval_scope or {}),
        "retrieval_pins": dict(retrieval_pins or {}),
        "synthesis_policy_pack_id": policy_pack_id,
        "selection_policy": caps,
        "replay_pins": dict(replay_pins or {}),
    }
    if idempotency_key:
        envelope["idempotency_key"] = str(idempotency_key).strip()
    if substrate_pipeline_run_id:
        envelope["substrate_pipeline_run_id"] = str(substrate_pipeline_run_id)
    if isinstance(pinned, dict):
        envelope["pinned_retrieval_receipt"] = dict(pinned)
    if body.get("synthesis_prompt_overrides") is not None:
        envelope["synthesis_prompt_overrides"] = dict(body["synthesis_prompt_overrides"])
    if body.get("expected_synthesis_job_replay_identity") is not None:
        envelope["expected_synthesis_job_replay_identity"] = str(
            body["expected_synthesis_job_replay_identity"],
        )
    envelope["_synthesis_policy_pack_digest"] = policy_pack_digest
    return envelope


def coerce_body_to_synthesis_job_envelope_v1(
    body: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Accept full envelope or minimal admin debugger body."""
    if body.get("schema_version") is not None and body.get("schema_version") != (
        SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
    ):
        validate_synthesis_job_envelope_schema_version_v1(body)
    if body.get("schema_version") == SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1:
        return normalize_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
    wl, it = resolve_synthesis_workload_and_intent_v1(body)
    minimal = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": wl,
        "synthesis_intent": it,
        "execution_partition": str(body.get("execution_partition") or "authoritative"),
        "retrieval_scope": dict(body.get("retrieval_scope") or {}),
        "retrieval_pins": dict(body.get("retrieval_pins") or {}),
        "synthesis_policy_pack_id": body.get("synthesis_policy_pack_id"),
        "selection_policy": dict(body.get("selection_policy") or {}),
        "idempotency_key": body.get("idempotency_key"),
        "substrate_pipeline_run_id": body.get("substrate_pipeline_run_id"),
        "pinned_retrieval_receipt": body.get("pinned_retrieval_receipt"),
        "replay_pins": dict(body.get("replay_pins") or {}),
        "synthesis_prompt_overrides": body.get("synthesis_prompt_overrides"),
        "expected_synthesis_job_replay_identity": body.get("expected_synthesis_job_replay_identity"),
    }
    return normalize_synthesis_job_envelope_v1(minimal, tenant_id=tenant_id)


def compute_synthesis_job_envelope_digest_v1(envelope: Mapping[str, Any]) -> str:
    """Canonical envelope digest for idempotency (**SYN-FSM-04**)."""
    body = {
        "schema_version": envelope.get("schema_version"),
        "tenant_id": envelope.get("tenant_id"),
        "synthesis_workload_class": envelope.get("synthesis_workload_class"),
        "synthesis_intent": envelope.get("synthesis_intent"),
        "execution_partition": envelope.get("execution_partition"),
        "retrieval_scope": envelope.get("retrieval_scope") or {},
        "retrieval_pins": envelope.get("retrieval_pins") or {},
        "synthesis_policy_pack_id": envelope.get("synthesis_policy_pack_id"),
        "selection_policy": envelope.get("selection_policy") or {},
        "substrate_pipeline_run_id": envelope.get("substrate_pipeline_run_id"),
        "pinned_retrieval_receipt_digest": (
            hash_reasoning_canonical_json_sha256_v1(dict(envelope["pinned_retrieval_receipt"]))
            if isinstance(envelope.get("pinned_retrieval_receipt"), dict)
            else None
        ),
    }
    return hash_reasoning_canonical_json_sha256_v1(body)
