"""Phase 08 P08-10 — deterministic PLAN + RETRIEVE via Phase **07** only.

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md`` §Orchestrator.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.query_contract import addressing_has_resolvable_ref_v1
from vector.domains.cortex.synthesis.synthesis_ingress import (
    build_retrieval_evidence_ingress_v1,
    compute_retrieval_ingress_digest_v1,
    enforce_retrieval_evidence_ingress_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    selection_policy_caps_for_synthesis_workload_v1,
    validate_synthesis_workload_class_v1,
)

PHASE08_SYNTHESIS_QUERY_PLAN_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_RETRIEVE01_GATE_ID_V1: Final[str] = "G-P08-RETRIEVE-01"

SD_CAP_RETRIEVAL_V1: Final[str] = "SD-CAP-RETRIEVAL"

PHASE08_RETRIEVAL_PLAN_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md"
)

_RETRIEVAL_LEGALITY_ORDINALS_V1: Final[dict[str, int]] = {
    "retrieval_replay_safe": 0,
    "retrieval_degraded": 1,
    "retrieval_partial": 2,
    "retrieval_unverifiable": 3,
    "retrieval_forbidden": 4,
}

_SYNTHESIS_TO_PRIMARY_RETRIEVAL_WORKLOAD_V1: Final[dict[str, str]] = {
    "execution_understanding": "causal_chain",
    "operational_synthesis": "degradation_survey",
    "execution_narrative": "causal_chain",
    "management_intelligence": "degradation_survey",
    "continuity_assessment": "ownership_continuity",
    "degradation_brief": "causal_chain",
    "replay_equivalence_synthesis": "replay_equivalence",
    "pipeline_default": "causal_chain",
}


class SynthesisQueryPlanError(ValueError):
    """Fail-closed synthesis retrieval plan / fan-out execution."""

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


def _repo_root_v1() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "synthesis").is_dir():
            return root
    return start.parents[6]


def load_synthesis_policy_pack_v1(
    *,
    policy_pack_id: str | None = None,
) -> dict[str, Any]:
    """Load ``SynthesisPolicyPackV1`` fixture (default pack until pack service ships)."""
    pack_id = policy_pack_id or DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1
    path = _repo_root_v1() / "DOCS" / "cortex" / "synthesis" / "fixtures" / f"{pack_id}.json"
    if not path.is_file():
        raise SynthesisQueryPlanError(
            "synthesis_policy_pack_not_found",
            detail={"policy_pack_id": pack_id, "path": str(path)},
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SynthesisQueryPlanError("invalid_synthesis_policy_pack")
    return raw


def map_synthesis_workload_to_retrieval_workload_v1(synthesis_workload_class: str) -> str:
    """Map synthesis workload → primary Phase **07** ``workload_class``."""
    wl = validate_synthesis_workload_class_v1(synthesis_workload_class)
    return _SYNTHESIS_TO_PRIMARY_RETRIEVAL_WORKLOAD_V1.get(wl, "causal_chain")


def build_synthesis_retrieval_plan_v1(envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
    """PLAN phase — ordered retrieval sub-query descriptors (policy fan-out + caps)."""
    wl = str(envelope["synthesis_workload_class"])
    scope = dict(envelope.get("retrieval_scope") or {})
    caps = dict(envelope.get("selection_policy") or {})
    if not caps:
        caps = selection_policy_caps_for_synthesis_workload_v1(wl)
    max_sub = int(caps.get("max_retrieval_subqueries", 8))
    primary_retrieval_wl = map_synthesis_workload_to_retrieval_workload_v1(wl)
    plan: list[dict[str, Any]] = [
        {
            "plan_index": 0,
            "role": "primary",
            "synthesis_workload_class": wl,
            "retrieval_workload_class": primary_retrieval_wl,
            "retrieval_intent": str(envelope["synthesis_intent"]),
            "retrieval_scope": scope,
            "max_retrieval_subqueries": max_sub,
        },
    ]
    pack = load_synthesis_policy_pack_v1(
        policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
    )
    fanout_rules = pack.get("retrieval_fanout_rules")
    if not isinstance(fanout_rules, list):
        return plan
    deferred_fanout: list[dict[str, Any]] = []
    for rule in fanout_rules:
        if not isinstance(rule, Mapping):
            continue
        if str(rule.get("when_workload") or "") != wl:
            continue
        add_wl = str(rule.get("add_workload") or "").strip()
        if not add_wl:
            continue
        deferred_fanout.append(
            {
                "plan_index": len(plan) + len(deferred_fanout),
                "role": "fanout",
                "synthesis_workload_class": wl,
                "retrieval_workload_class": add_wl,
                "retrieval_intent": str(rule.get("intent") or envelope["synthesis_intent"]),
                "retrieval_scope": dict(scope),
                "fanout_rule": dict(rule),
            },
        )
    for row in deferred_fanout:
        if len(plan) >= max_sub:
            break
        row["plan_index"] = len(plan)
        plan.append(row)
    return plan


def list_synthesis_retrieval_plan_cap_violations_v1(
    envelope: Mapping[str, Any],
    *,
    unconstrained_plan_count: int,
) -> list[dict[str, Any]]:
    """Emit ``SD-CAP-RETRIEVAL`` rows when fan-out rules exceed ``max_retrieval_subqueries``."""
    wl = str(envelope["synthesis_workload_class"])
    caps = dict(envelope.get("selection_policy") or {})
    if not caps:
        caps = selection_policy_caps_for_synthesis_workload_v1(wl)
    max_sub = int(caps.get("max_retrieval_subqueries", 8))
    if unconstrained_plan_count <= max_sub:
        return []
    return [
        {
            "synthesis_omission_class": SD_CAP_RETRIEVAL_V1,
            "sd_code": SD_CAP_RETRIEVAL_V1,
            "reason": "retrieval_fanout_truncated",
            "max_retrieval_subqueries": max_sub,
            "requested_subqueries": unconstrained_plan_count,
        },
    ]


def build_retrieval_query_envelope_for_plan_item_v1(
    envelope: Mapping[str, Any],
    plan_item: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Build Phase **07** query envelope body for a plan row."""
    scope = dict(plan_item.get("retrieval_scope") or envelope.get("retrieval_scope") or {})
    pins = dict(envelope.get("retrieval_pins") or {})
    body: dict[str, Any] = {
        "schema_version": 1,
        "tenant_id": str(tenant_id or envelope.get("tenant_id") or ""),
        "workload_class": str(plan_item["retrieval_workload_class"]),
        "intent": str(plan_item.get("retrieval_intent") or envelope["synthesis_intent"]),
        "execution_partition": str(envelope["execution_partition"]),
        "replay_pins": pins,
    }
    addressing: dict[str, Any] = {}
    if isinstance(scope.get("addressing"), Mapping):
        addressing.update(dict(scope["addressing"]))
    for key in (
        "retrieval_lookup_id",
        "causal_chain_id",
        "retrieval_chain_ref",
        "retrieval_window_ref",
        "retrieval_walk_ref",
        "retrieval_lineage_ref",
    ):
        if scope.get(key) and key not in addressing:
            addressing[key] = scope[key]
    if addressing:
        body["addressing"] = addressing
    if scope.get("retrieval_lookup_id"):
        body["retrieval_lookup_id"] = scope["retrieval_lookup_id"]
    if scope.get("expected_replay_identity"):
        body["expected_replay_identity"] = scope["expected_replay_identity"]
    if pins.get("index_epoch"):
        body.setdefault("index_epoch", pins["index_epoch"])
    return body


def build_retrieval_subquery_receipt_row_v1(
    *,
    plan_item: Mapping[str, Any],
    retrieval_response: Mapping[str, Any],
    retrieval_ingress_digest: str,
) -> dict[str, Any]:
    """Per sub-query receipt row persisted on the synthesis job."""
    receipt = retrieval_response.get("retrieval_query_receipt")
    receipt_digest = receipt.get("receipt_digest") if isinstance(receipt, Mapping) else None
    return {
        "plan_index": int(plan_item.get("plan_index", 0)),
        "role": str(plan_item.get("role") or "primary"),
        "retrieval_workload_class": plan_item.get("retrieval_workload_class"),
        "retrieval_intent": plan_item.get("retrieval_intent"),
        PHASE07_REPLAY_IDENTITY_FIELD_V1: str(
            retrieval_response.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "",
        ),
        "retrieval_ingress_digest": retrieval_ingress_digest,
        "retrieval_query_receipt_digest": receipt_digest,
        "retrieval_legality_class": retrieval_response.get("retrieval_legality_class"),
        "hit_count": len(retrieval_response.get("retrieval_evidence_hits") or [])
        if isinstance(retrieval_response.get("retrieval_evidence_hits"), list)
        else 0,
    }


def _max_retrieval_legality_v1(classes: Sequence[str]) -> str:
    if not classes:
        return "retrieval_replay_safe"
    return max(classes, key=lambda c: _RETRIEVAL_LEGALITY_ORDINALS_V1.get(c, 99))


def merge_retrieval_responses_v1(
    responses: Sequence[Mapping[str, Any]],
    *,
    primary_index: int = 0,
) -> dict[str, Any]:
    """Merge Phase **07** responses into a single ingress-shaped retrieval dict."""
    merged_hits: list[dict[str, Any]] = []
    merged_omissions: list[dict[str, Any]] = []
    legalities: list[str] = []
    primary: Mapping[str, Any] = responses[primary_index] if responses else {}
    for resp in responses:
        if not isinstance(resp, Mapping):
            continue
        leg = resp.get("retrieval_legality_class")
        if isinstance(leg, str):
            legalities.append(leg)
        hits = resp.get("retrieval_evidence_hits")
        if isinstance(hits, list):
            for hit in hits:
                if isinstance(hit, Mapping):
                    merged_hits.append(dict(hit))
        omissions = resp.get("retrieval_omission_rows")
        if omissions is None:
            omissions = resp.get("omissions")
        if isinstance(omissions, list):
            for row in omissions:
                if isinstance(row, Mapping):
                    merged_omissions.append(dict(row))
    merged: dict[str, Any] = {
        "schema_version": 1,
        "retrieval_legality_class": _max_retrieval_legality_v1(legalities),
        PHASE07_REPLAY_IDENTITY_FIELD_V1: primary.get(PHASE07_REPLAY_IDENTITY_FIELD_V1),
        "retrieval_evidence_hits": merged_hits,
        "retrieval_omission_rows": merged_omissions,
        "retrieval_policy_pack_digest": primary.get("retrieval_policy_pack_digest"),
        "retrieval_query_receipt": primary.get("retrieval_query_receipt"),
        "non_authoritative": any(bool(r.get("non_authoritative")) for r in responses if isinstance(r, Mapping)),
        "merged_subquery_count": len(responses),
    }
    return merged


def _plan_item_has_resolvable_addressing_v1(
    envelope: Mapping[str, Any],
    plan_item: Mapping[str, Any],
) -> bool:
    body = build_retrieval_query_envelope_for_plan_item_v1(envelope, plan_item)
    if str(body.get("retrieval_lookup_id") or "").strip():
        return True
    addressing = body.get("addressing")
    return isinstance(addressing, Mapping) and addressing_has_resolvable_ref_v1(addressing)


def execute_synthesis_retrieval_plan_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    plan: Sequence[Mapping[str, Any]],
    job_envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """RETRIEVE phase — execute plan via ``execute_retrieval_query_v1`` (Phase **07** only)."""
    from vector.domains.cortex.synthesis.synthesis_retrieval_client import (
        execute_retrieval_query_for_synthesis_v1,
        is_retrieval_query_execution_error,
    )

    job_env = dict(job_envelope or envelope)
    plan_list = [row for row in plan if isinstance(row, Mapping)]
    if not plan_list or not any(
        _plan_item_has_resolvable_addressing_v1(envelope, row) for row in plan_list
    ):
        empty = {
            "schema_version": 1,
            "retrieval_evidence_hits": [],
            "retrieval_omission_rows": [
                {
                    "synthesis_omission_class": "SD-SCOPE-EMPTY",
                    "sd_code": "SD-SCOPE-EMPTY",
                    "reason": "retrieval_scope_unaddressed",
                },
            ],
            "retrieval_legality_class": "retrieval_replay_safe",
            PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:synthesis-scope-empty",
        }
        ingress = build_retrieval_evidence_ingress_v1(
            empty,
            job_execution_partition=str(envelope["execution_partition"]),
        )
        ingress["retrieval_evidence_hits"] = []
        return {
            "schema_version": PHASE08_SYNTHESIS_QUERY_PLAN_RUNTIME_SCHEMA_VERSION,
            "gate_id": GP08_RETRIEVE01_GATE_ID_V1,
            "retrieval_subqueries": [],
            "retrieval_responses": [],
            "merged_retrieval_response": empty,
            "retrieval_ingress": ingress,
            "retrieval_ingress_digest": compute_retrieval_ingress_digest_v1(ingress),
            "synthesis_omission_rows": list(ingress.get("synthesis_omission_rows") or []),
        }
    responses: list[dict[str, Any]] = []
    subquery_rows: list[dict[str, Any]] = []
    for item in plan_list:
        if not _plan_item_has_resolvable_addressing_v1(envelope, item):
            continue
        query_body = build_retrieval_query_envelope_for_plan_item_v1(
            envelope,
            item,
            tenant_id=tenant_id,
        )
        try:
            resp = execute_retrieval_query_for_synthesis_v1(
                session,
                tenant_id=tenant_id,
                envelope_body=query_body,
            )
        except Exception as exc:
            if not is_retrieval_query_execution_error(exc):
                raise
            raise SynthesisQueryPlanError(
                "retrieval_subquery_failed",
                http_status=400,
                detail={
                    "plan_index": item.get("plan_index"),
                    "retrieval_workload_class": item.get("retrieval_workload_class"),
                    "code": getattr(exc, "code", str(exc)),
                },
            ) from exc
        ingress_row = build_retrieval_evidence_ingress_v1(
            resp,
            job_execution_partition=str(envelope["execution_partition"]),
        )
        digest = compute_retrieval_ingress_digest_v1(ingress_row)
        enforce_retrieval_evidence_ingress_v1(resp, job_envelope=job_env)
        subquery_rows.append(
            build_retrieval_subquery_receipt_row_v1(
                plan_item=item,
                retrieval_response=resp,
                retrieval_ingress_digest=digest,
            ),
        )
        responses.append(dict(resp))
    merged = merge_retrieval_responses_v1(responses)
    ingress = build_retrieval_evidence_ingress_v1(
        merged,
        job_execution_partition=str(envelope["execution_partition"]),
    )
    ingress["retrieval_evidence_hits"] = list(merged.get("retrieval_evidence_hits") or [])
    retrieval_ingress_digest = compute_retrieval_ingress_digest_v1(ingress)
    cap_rows = list_synthesis_retrieval_plan_cap_violations_v1(
        envelope,
        unconstrained_plan_count=_unconstrained_fanout_plan_count_v1(envelope),
    )
    if cap_rows:
        existing_sd = list(ingress.get("synthesis_omission_rows") or [])
        ingress["synthesis_omission_rows"] = existing_sd + cap_rows
    return {
        "schema_version": PHASE08_SYNTHESIS_QUERY_PLAN_RUNTIME_SCHEMA_VERSION,
        "gate_id": GP08_RETRIEVE01_GATE_ID_V1,
        "retrieval_subqueries": subquery_rows,
        "retrieval_responses": responses,
        "merged_retrieval_response": merged,
        "retrieval_ingress": ingress,
        "retrieval_ingress_digest": retrieval_ingress_digest,
        "synthesis_omission_rows": list(ingress.get("synthesis_omission_rows") or []),
    }


def _unconstrained_fanout_plan_count_v1(envelope: Mapping[str, Any]) -> int:
    wl = str(envelope["synthesis_workload_class"])
    pack = load_synthesis_policy_pack_v1(
        policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
    )
    fanout = pack.get("retrieval_fanout_rules")
    extra = 0
    if isinstance(fanout, list):
        extra = sum(1 for r in fanout if isinstance(r, Mapping) and str(r.get("when_workload")) == wl)
    return 1 + extra


def build_synthesis_retrieval_plan_catalog_v1() -> dict[str, Any]:
    """Admin catalog — PLAN + RETRIEVE law."""
    pack = load_synthesis_policy_pack_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_retrieval_plan_v1",
        "phase08_synthesis_query_plan_runtime_schema_version": (
            PHASE08_SYNTHESIS_QUERY_PLAN_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_RETRIEVE01_GATE_ID_V1,
        "spec_ref": PHASE08_RETRIEVAL_PLAN_SPEC_REF_V1,
        "synthesis_to_primary_retrieval_workload": dict(_SYNTHESIS_TO_PRIMARY_RETRIEVAL_WORKLOAD_V1),
        "retrieval_fanout_rules": list(pack.get("retrieval_fanout_rules") or []),
        "max_retrieval_subqueries_default": int(
            (pack.get("caps") or {}).get("max_retrieval_subqueries", 8),
        ),
        "sd_cap_retrieval": SD_CAP_RETRIEVAL_V1,
    }


def build_synthesis_retrieval_plan_preview_v1(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Admin preview — plan rows without executing Phase **07**."""
    plan = build_synthesis_retrieval_plan_v1(envelope)
    envelopes = [
        build_retrieval_query_envelope_for_plan_item_v1(envelope, row)
        for row in plan
        if isinstance(row, Mapping)
    ]
    return {
        "surface_kind": "synthesis_retrieval_plan_preview",
        "gate_id": GP08_RETRIEVE01_GATE_ID_V1,
        "retrieval_plan_count": len(plan),
        "retrieval_plan": list(plan),
        "retrieval_query_envelopes": envelopes,
        "cap_violations": list_synthesis_retrieval_plan_cap_violations_v1(
            envelope,
            unconstrained_plan_count=_unconstrained_fanout_plan_count_v1(envelope),
        ),
    }


def _retrieve_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_RETRIEVE01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_retrieve01_plan_fanout_static() -> dict[str, Any]:
    errors: list[str] = []
    env = {
        "synthesis_workload_class": "execution_understanding",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {"retrieval_lookup_id": "sha256:" + "a" * 64},
        "synthesis_policy_pack_id": DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    }
    plan = build_synthesis_retrieval_plan_v1(env)
    if len(plan) < 2:
        errors.append("expected_fanout_for_execution_understanding")
    if plan[0].get("role") != "primary":
        errors.append("primary_must_be_index_0")
    roles = [str(r.get("retrieval_workload_class")) for r in plan]
    if "lineage_explorer" not in roles:
        errors.append("expected_lineage_explorer_fanout")
    capped_env = {
        **env,
        "selection_policy": {"max_retrieval_subqueries": 1},
    }
    capped_plan = build_synthesis_retrieval_plan_v1(capped_env)
    if len(capped_plan) != 1:
        errors.append("cap_should_truncate_fanout")
    cap_rows = list_synthesis_retrieval_plan_cap_violations_v1(
        capped_env,
        unconstrained_plan_count=_unconstrained_fanout_plan_count_v1(capped_env),
    )
    if not cap_rows:
        errors.append("expected_sd_cap_retrieval")
    return _retrieve_meta("gp08_retrieve01_plan_fanout", errors)


def verify_gp08_retrieve01_merge_responses_static() -> dict[str, Any]:
    errors: list[str] = []
    a = {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "x" * 64,
        "retrieval_evidence_hits": [{"retrieval_lookup_id": "sha256:01"}],
        "retrieval_omission_rows": [],
    }
    b = {
        "retrieval_legality_class": "retrieval_degraded",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "y" * 64,
        "retrieval_evidence_hits": [{"retrieval_lookup_id": "sha256:02"}],
        "retrieval_omission_rows": [{"retrieval_omission_class": "RD-X"}],
    }
    merged = merge_retrieval_responses_v1([a, b])
    if merged["retrieval_legality_class"] != "retrieval_degraded":
        errors.append("merged_legality_should_be_worst")
    if len(merged["retrieval_evidence_hits"]) != 2:
        errors.append("merged_hit_count")
    if merged[PHASE07_REPLAY_IDENTITY_FIELD_V1] != "x" * 64:
        errors.append("primary_replay_identity_preserved")
    return _retrieve_meta("gp08_retrieve01_merge_responses", errors)


def verify_gp08_retrieve01_query_envelope_static() -> dict[str, Any]:
    errors: list[str] = []
    env = {
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_pins": {"index_epoch": "epoch-1"},
        "retrieval_scope": {
            "retrieval_lookup_id": "sha256:" + "b" * 64,
            "expected_replay_identity": "c" * 64,
        },
    }
    plan = build_synthesis_retrieval_plan_v1(env)
    body = build_retrieval_query_envelope_for_plan_item_v1(env, plan[0])
    if body.get("workload_class") != "causal_chain":
        errors.append("workload_map_mismatch")
    addr = body.get("addressing")
    env_scope = env.get("retrieval_scope")
    expected_lookup = (
        env_scope.get("retrieval_lookup_id")
        if isinstance(env_scope, Mapping)
        else None
    )
    if not isinstance(addr, Mapping) or addr.get("retrieval_lookup_id") != expected_lookup:
        errors.append("addressing_missing_lookup_id")
    digest_a = hash_reasoning_canonical_json_sha256_v1(body)
    digest_b = hash_reasoning_canonical_json_sha256_v1(body)
    if digest_a != digest_b:
        errors.append("envelope_not_stable")
    return _retrieve_meta("gp08_retrieve01_query_envelope", errors)
