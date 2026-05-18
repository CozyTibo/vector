"""Phase 08 P08-08 — synthesis replay identity + receipt law (**SYN-REP-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-replay-equivalence-spec.md``.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.normative import (
    PHASE08_REPLAY_IDENTITY_FIELD_V1,
    PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

SYNTHESIS_JOB_RECEIPT_SCHEMA_VERSION_V1: Final[int] = 1

SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1: Final[str] = "syn-orchestrator-v1-stub"

PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_REPLAY_01_GATE_ID_V1: Final[str] = "G-P08-REPLAY-01"

GP08_REPLAY_02_GATE_ID_V1: Final[str] = "G-P08-REPLAY-02"

SYN_REP_01_RULE_ID_V1: Final[str] = "SYN-REP-01"

SD_REPLAY_DRIFT_V1: Final[str] = "SD-REPLAY-DRIFT"

SD_REPLAY_TWIN_V1: Final[str] = "SD-REPLAY-TWIN"

PHASE08_REPLAY_EQUIVALENCE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-replay-equivalence-spec.md"
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")

_SYNTHESIS_REPLAY_IDENTITY_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "llm_completion_text",
        "completion_text",
        "raw_llm_output",
        "narrative_blocks",
        "claims_text",
    }
)

SYNTHESIS_REPLAY_PIN_FIELD_IDS_V1: Final[tuple[str, ...]] = (
    "synthesis_policy_pack_digest",
    "retrieval_query_replay_identity",
    "retrieval_ingress_digest",
    "published_index_epoch",
    "tcre_policy_bundle_digest",
    "index_epoch",
    "expected_synthesis_job_replay_identity",
)

_SYNTHESIS_REPLAY_DIVERGENCE_TOTAL_V1: int = 0


class SynthesisReplayEquivalenceError(ValueError):
    """Fail-closed synthesis replay identity / twin law."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int = 403,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def get_synthesis_replay_divergence_total_v1() -> int:
    return _SYNTHESIS_REPLAY_DIVERGENCE_TOTAL_V1


def record_synthesis_replay_divergence_v1(
    *,
    tenant_id: str,
    synthesis_job_replay_identity_a: str,
    synthesis_job_replay_identity_b: str,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Record **G-P08-REPLAY-01** divergence (observability counter)."""
    global _SYNTHESIS_REPLAY_DIVERGENCE_TOTAL_V1
    _SYNTHESIS_REPLAY_DIVERGENCE_TOTAL_V1 += 1
    return {
        "event": "synthesis_replay_divergence",
        "gate_id": GP08_REPLAY_01_GATE_ID_V1,
        "tenant_id": tenant_id,
        "synthesis_job_replay_identity_a": synthesis_job_replay_identity_a,
        "synthesis_job_replay_identity_b": synthesis_job_replay_identity_b,
        "detail": dict(detail or {}),
    }


def normalize_sorted_string_list_v1(values: Sequence[str]) -> list[str]:
    return sorted({str(v).strip() for v in values if str(v).strip()})


def normalize_retrieval_subquery_replay_identities_v1(
    retrieval_subqueries: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Sorted ``retrieval_query_replay_identity`` list from sub-query rows."""
    ids = [
        str(row.get("retrieval_query_replay_identity") or row.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
        for row in retrieval_subqueries
        if isinstance(row, Mapping)
    ]
    return normalize_sorted_string_list_v1(ids)


def primary_retrieval_query_replay_identity_v1(
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    *,
    retrieval_ingress: Mapping[str, Any] | None = None,
) -> str:
    """Primary upstream retrieval replay identity (first sub-query or ingress copy)."""
    for row in retrieval_subqueries:
        if isinstance(row, Mapping):
            rid = str(
                row.get("retrieval_query_replay_identity")
                or row.get(PHASE07_REPLAY_IDENTITY_FIELD_V1)
                or "",
            ).strip()
            if rid:
                return rid
    if isinstance(retrieval_ingress, Mapping):
        copy = retrieval_ingress.get("retrieval_legality_copy")
        if isinstance(copy, Mapping):
            pass
        leg_copy = retrieval_ingress.get(PHASE07_REPLAY_IDENTITY_FIELD_V1)
        if leg_copy:
            return str(leg_copy)
    return ""


def compute_claim_slot_plan_digest_v1(claim_slots: Sequence[Mapping[str, Any]]) -> str:
    """Structural claim slot plan digest (no LLM text)."""
    slots: list[dict[str, Any]] = []
    for row in claim_slots:
        if not isinstance(row, Mapping):
            continue
        slots.append(
            {
                "claim_id": row.get("claim_id"),
                "claim_kind": row.get("claim_kind"),
                "citation_placeholders": row.get("citation_placeholders") or [],
            },
        )
    return hash_reasoning_canonical_json_sha256_v1({"claim_slots": slots})


def build_synthesis_job_replay_identity_vector_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_ingress_digest: str | None,
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None = None,
    claim_slots: Sequence[Mapping[str, Any]] | None = None,
    llm_invocations: Sequence[Mapping[str, Any]] | None = None,
    sd_codes_sorted: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Canonical JSON scope for ``synthesis_job_replay_identity`` (**SYN-REP-01** — pins only)."""
    policy_digest = str(
        envelope.get("_synthesis_policy_pack_digest")
        or envelope.get("synthesis_policy_pack_digest")
        or synthesis_policy_pack_digest_v1(),
    )
    pins = envelope.get("retrieval_pins")
    retrieval_pins = dict(pins) if isinstance(pins, Mapping) else {}
    prompt_hashes = normalize_sorted_string_list_v1(
        [str(row.get("prompt_hash") or "") for row in (llm_invocations or ()) if isinstance(row, Mapping)],
    )
    model_route_ids = normalize_sorted_string_list_v1(
        [str(row.get("model_route_id") or "") for row in (llm_invocations or ()) if isinstance(row, Mapping)],
    )
    vector: dict[str, Any] = {
        "synthesis_policy_pack_digest": policy_digest,
        "synthesis_workload_class": envelope.get("synthesis_workload_class"),
        "synthesis_intent": envelope.get("synthesis_intent"),
        "execution_partition": envelope.get("execution_partition"),
        PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1: primary_retrieval_query_replay_identity_v1(
            retrieval_subqueries,
            retrieval_ingress=retrieval_ingress if isinstance(retrieval_ingress, Mapping) else None,
        ),
        "retrieval_subquery_replay_identities": normalize_retrieval_subquery_replay_identities_v1(
            retrieval_subqueries,
        ),
        "retrieval_ingress_digest": retrieval_ingress_digest or "",
        "claim_slot_plan_digest": compute_claim_slot_plan_digest_v1(claim_slots or ()),
        "prompt_hashes": prompt_hashes,
        "model_route_ids": model_route_ids,
        "synthesis_orchestrator_build_id": SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1,
        "published_index_epoch": str(retrieval_pins.get("published_index_epoch") or ""),
        "tcre_policy_bundle_digest": str(retrieval_pins.get("tcre_policy_bundle_digest") or ""),
        "index_epoch": str(retrieval_pins.get("index_epoch") or ""),
        "sd_codes_sorted": normalize_sorted_string_list_v1(list(sd_codes_sorted or ())),
    }
    for forbidden in _SYNTHESIS_REPLAY_IDENTITY_FORBIDDEN_KEYS:
        if forbidden in vector:
            msg = f"forbidden_replay_identity_key:{forbidden}"
            raise SynthesisReplayEquivalenceError(msg)
    return vector


def hash_synthesis_job_replay_identity_v1(vector: Mapping[str, Any]) -> str:
    for forbidden in _SYNTHESIS_REPLAY_IDENTITY_FORBIDDEN_KEYS:
        if forbidden in vector:
            raise SynthesisReplayEquivalenceError(f"forbidden_replay_identity_key:{forbidden}")
    return hash_reasoning_canonical_json_sha256_v1(vector)


def compute_synthesis_job_replay_identity_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_ingress_digest: str | None,
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None = None,
    claim_slots: Sequence[Mapping[str, Any]] | None = None,
    llm_invocations: Sequence[Mapping[str, Any]] | None = None,
    sd_codes_sorted: Sequence[str] | None = None,
) -> str:
    """64-char hex ``synthesis_job_replay_identity`` after RECEIPT (**SYN-REP-01**)."""
    vector = build_synthesis_job_replay_identity_vector_v1(
        envelope=envelope,
        retrieval_ingress_digest=retrieval_ingress_digest,
        retrieval_subqueries=retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
        claim_slots=claim_slots,
        llm_invocations=llm_invocations,
        sd_codes_sorted=sd_codes_sorted,
    )
    return hash_synthesis_job_replay_identity_v1(vector)


def build_retrieval_receipt_embed_v1(
    *,
    retrieval_ingress: Mapping[str, Any] | None,
    retrieval_subqueries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Digest-pinned retrieval receipt embed for artifacts (**SYN-REP-03** prep)."""
    primary_rqid = primary_retrieval_query_replay_identity_v1(
        retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
    )
    embed: dict[str, Any] = {
        "schema_version": 1,
        PHASE07_REPLAY_IDENTITY_FIELD_V1: primary_rqid,
        "retrieval_subquery_replay_identities": normalize_retrieval_subquery_replay_identities_v1(
            retrieval_subqueries,
        ),
        "retrieval_ingress_digest": (
            str(retrieval_ingress.get("retrieval_ingress_digest") or "")
            if isinstance(retrieval_ingress, Mapping)
            else ""
        ),
    }
    if isinstance(retrieval_ingress, Mapping):
        rqd = retrieval_ingress.get("retrieval_query_receipt_digest")
        if rqd:
            embed["retrieval_query_receipt_digest"] = str(rqd)
    embed["retrieval_receipt_embed_digest"] = hash_reasoning_canonical_json_sha256_v1(embed)
    return embed


def list_synthesis_expected_replay_identity_violations_v1(
    envelope: Mapping[str, Any],
    *,
    computed_identity: str,
) -> list[str]:
    """Envelope ``expected_synthesis_job_replay_identity`` pin check."""
    expected = envelope.get("expected_synthesis_job_replay_identity")
    if expected is None or not str(expected).strip():
        return []
    if str(expected).strip() != computed_identity:
        return [
            f"expected_synthesis_job_replay_identity_mismatch:"
            f"{expected}!={computed_identity}",
        ]
    return []


def enforce_synthesis_expected_replay_identity_v1(
    envelope: Mapping[str, Any],
    *,
    computed_identity: str,
) -> None:
    violations = list_synthesis_expected_replay_identity_violations_v1(
        envelope,
        computed_identity=computed_identity,
    )
    if violations:
        raise SynthesisReplayEquivalenceError(
            "expected_synthesis_job_replay_identity_mismatch",
            detail={"violations": violations},
        )


def verify_retrieval_receipt_embed_v1(
    receipt_embed: Mapping[str, Any],
    *,
    live_retrieval_response: Mapping[str, Any],
) -> dict[str, Any]:
    """**SYN-REP-03** — verify embed matches live retrieval response replay identity."""
    violations: list[str] = []
    embed_rid = str(receipt_embed.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    live_rid = str(live_retrieval_response.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    if embed_rid and live_rid and embed_rid != live_rid:
        violations.append("retrieval_replay_identity_mismatch")
    embed_digest = str(receipt_embed.get("retrieval_ingress_digest") or "")
    live_digest = str(live_retrieval_response.get("retrieval_policy_pack_digest") or "")
    if embed_digest and live_digest and embed_digest != live_digest:
        violations.append("retrieval_policy_digest_mismatch")
    return {
        "syn_rep_rule": "SYN-REP-03",
        "passed": len(violations) == 0,
        "violations": violations,
    }


def apply_syn_rep02_retrieval_twin_legality_floor_v1(
    synthesis_legality_class: str,
    *,
    gp08_replay_01_passed: bool,
) -> str:
    """**SYN-REP-02** — retrieval twin divergence MUST NOT claim ``synthesis_replay_safe``."""
    if not gp08_replay_01_passed and synthesis_legality_class == "synthesis_replay_safe":
        return "synthesis_degraded"
    return synthesis_legality_class


def compare_gp08_replay_01_double_run_v1(
    run_a: Mapping[str, Any],
    run_b: Mapping[str, Any],
) -> None:
    """**G-P08-REPLAY-01** — require identical synthesis replay identity + receipt digest."""
    id_a = str(run_a.get(PHASE08_REPLAY_IDENTITY_FIELD_V1) or "")
    id_b = str(run_b.get(PHASE08_REPLAY_IDENTITY_FIELD_V1) or "")
    if id_a != id_b:
        raise SynthesisReplayEquivalenceError(
            f"{GP08_REPLAY_01_GATE_ID_V1}: synthesis_job_replay_identity mismatch",
            detail={"a": id_a, "b": id_b},
        )
    rec_a = run_a.get("synthesis_job_receipt") or {}
    rec_b = run_b.get("synthesis_job_receipt") or {}
    if not isinstance(rec_a, Mapping) or not isinstance(rec_b, Mapping):
        raise SynthesisReplayEquivalenceError("synthesis_job_receipt_must_be_object")
    dig_a = str(rec_a.get("receipt_digest") or "")
    dig_b = str(rec_b.get("receipt_digest") or "")
    if dig_a != dig_b:
        raise SynthesisReplayEquivalenceError(
            f"{GP08_REPLAY_01_GATE_ID_V1}: receipt_digest mismatch",
            detail={"a": dig_a, "b": dig_b},
        )


def synthesis_artifact_body_from_run_v1(run: Mapping[str, Any]) -> dict[str, Any]:
    """Best-effort artifact snapshot from a completed job run (for structural twin)."""
    embedded = run.get("synthesis_intelligence_artifact")
    if isinstance(embedded, Mapping):
        return dict(embedded)
    receipt = run.get("synthesis_job_receipt")
    rec = dict(receipt) if isinstance(receipt, Mapping) else {}
    return {
        "artifact_id": str(run.get("artifact_id") or rec.get("artifact_id") or ""),
        "artifact_digest": str(run.get("artifact_digest") or rec.get("artifact_digest") or ""),
        "claims": list(run.get("claims") or rec.get("claims") or []),
        "synthesis_citation_envelope": dict(
            run.get("synthesis_citation_envelope") or rec.get("synthesis_citation_envelope") or {},
        ),
        "synthesis_omission_rows": list(rec.get("synthesis_omission_rows") or []),
        "narrative_blocks": list(rec.get("narrative_blocks") or []),
    }


_STRUCTURAL_TWIN_VOLATILE_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "artifact_id",
        "lineage_chain_digest",
        "synthesis_omission_rows",
        "artifact_digest",
    },
)


def _structural_digest_for_twin_v1(artifact: Mapping[str, Any]) -> str:
    """Structural digest for twin compare — excludes per-run volatile artifact fields."""
    from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
        compute_synthesis_artifact_structural_body_v1,
    )

    body = compute_synthesis_artifact_structural_body_v1(artifact)
    scoped = dict(body)
    for key in _STRUCTURAL_TWIN_VOLATILE_KEYS_V1:
        scoped.pop(key, None)
    return hash_reasoning_canonical_json_sha256_v1(scoped)


def compare_synthesis_structural_artifact_twin_v1(
    artifact_a: Mapping[str, Any],
    artifact_b: Mapping[str, Any],
) -> dict[str, Any]:
    """Structural certification twin (**G-P08-REPLAY-01** §Twin) — no discourse-only text."""
    dig_a = _structural_digest_for_twin_v1(artifact_a)
    dig_b = _structural_digest_for_twin_v1(artifact_b)
    kinds_a = [
        str(c.get("claim_kind") or "")
        for c in artifact_a.get("claims") or []
        if isinstance(c, Mapping)
    ]
    kinds_b = [
        str(c.get("claim_kind") or "")
        for c in artifact_b.get("claims") or []
        if isinstance(c, Mapping)
    ]

    def _citation_signatures(artifact: Mapping[str, Any]) -> set[tuple[str, str]]:
        env = artifact.get("synthesis_citation_envelope")
        if not isinstance(env, Mapping):
            return set()
        out: set[tuple[str, str]] = set()
        for cit in env.get("citations") or []:
            if not isinstance(cit, Mapping):
                continue
            cid = str(cit.get("citation_id") or "")
            hit = str(
                cit.get("hit_digest")
                or cit.get("retrieval_lookup_id")
                or cit.get("evidence_hit_digest")
                or "",
            )
            if cid:
                out.add((cid, hit))
        return out

    def _sd_multiset(artifact: Mapping[str, Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in artifact.get("synthesis_omission_rows") or []:
            if not isinstance(row, Mapping):
                continue
            code = str(row.get("sd_code") or row.get("synthesis_omission_class") or "").strip()
            if code:
                counts[code] = counts.get(code, 0) + 1
        return counts

    cit_a = _citation_signatures(artifact_a)
    cit_b = _citation_signatures(artifact_b)
    sd_a = _sd_multiset(artifact_a)
    sd_b = _sd_multiset(artifact_b)
    wording_diff_only = dig_a == dig_b and artifact_a != artifact_b
    structural_passed = (
        dig_a == dig_b
        and kinds_a == kinds_b
        and cit_a == cit_b
        and sd_a == sd_b
    )
    return {
        "artifact_digest_a": dig_a,
        "artifact_digest_b": dig_b,
        "claim_kind_sequence_match": kinds_a == kinds_b,
        "citation_set_match": cit_a == cit_b,
        "sd_multiset_match": sd_a == sd_b,
        "structural_twin_passed": structural_passed,
        "wording_diff_only": wording_diff_only,
    }


def synthesis_replay_omissions_from_twin_diff_v1(
    twin: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Emit ``SD-REPLAY-TWIN`` when inline / operator structural twin diverges."""
    if twin.get("gp08_replay_proof_passed") is True:
        return []
    trigger = "gp08_replay_01_double_run"
    if twin.get("structural_twin_passed") is False:
        trigger = "structural_artifact_twin"
    elif twin.get("receipt_digest_a") != twin.get("receipt_digest_b"):
        trigger = "receipt_digest_mismatch"
    elif twin.get("synthesis_job_replay_identity_a") != twin.get("synthesis_job_replay_identity_b"):
        trigger = "synthesis_job_replay_identity_mismatch"
    return [
        {
            "sd_code": SD_REPLAY_TWIN_V1,
            "synthesis_omission_class": SD_REPLAY_TWIN_V1,
            "omission_semantics": "omitted_replay",
            "upstream_trigger": trigger,
            "gate_id": GP08_REPLAY_01_GATE_ID_V1,
        },
    ]


def build_synthesis_replay_equivalence_twin_diff_v1(
    run_a: Mapping[str, Any],
    run_b: Mapping[str, Any],
) -> dict[str, Any]:
    """Twin diff for ``prove`` intent / ``replay_equivalence_synthesis`` workload."""
    rec_a = run_a.get("synthesis_job_receipt") or {}
    rec_b = run_b.get("synthesis_job_receipt") or {}
    assert isinstance(rec_a, Mapping)
    assert isinstance(rec_b, Mapping)
    id_a = str(run_a.get(PHASE08_REPLAY_IDENTITY_FIELD_V1) or "")
    id_b = str(run_b.get(PHASE08_REPLAY_IDENTITY_FIELD_V1) or "")
    dig_a = str(rec_a.get("receipt_digest") or "")
    dig_b = str(rec_b.get("receipt_digest") or "")
    sub_a_raw = rec_a.get("retrieval_subqueries")
    sub_b_raw = rec_b.get("retrieval_subqueries")
    sub_a: list[Mapping[str, Any]] = (
        [row for row in sub_a_raw if isinstance(row, Mapping)]
        if isinstance(sub_a_raw, list)
        else []
    )
    sub_b: list[Mapping[str, Any]] = (
        [row for row in sub_b_raw if isinstance(row, Mapping)]
        if isinstance(sub_b_raw, list)
        else []
    )
    receipt_digest_match = dig_a == dig_b
    gp08_replay_01_passed = id_a == id_b and receipt_digest_match
    structural = compare_synthesis_structural_artifact_twin_v1(
        synthesis_artifact_body_from_run_v1(run_a),
        synthesis_artifact_body_from_run_v1(run_b),
    )
    structural_passed = bool(structural.get("structural_twin_passed"))
    gp08_replay_proof_passed = id_a == id_b and structural_passed
    return {
        "receipt_digest_a": dig_a,
        "receipt_digest_b": dig_b,
        "receipt_digest_match": receipt_digest_match,
        "synthesis_job_replay_identity_a": id_a,
        "synthesis_job_replay_identity_b": id_b,
        "retrieval_subquery_count_a": len(sub_a),
        "retrieval_subquery_count_b": len(sub_b),
        "retrieval_subquery_identities_match": (
            normalize_retrieval_subquery_replay_identities_v1(sub_a)
            == normalize_retrieval_subquery_replay_identities_v1(sub_b)
        ),
        "gp08_replay_01_passed": gp08_replay_01_passed,
        "structural_twin_passed": structural_passed,
        "gp08_replay_proof_passed": gp08_replay_proof_passed,
        "structural_twin_mode": "inline_twin",
        **structural,
    }


def build_synthesis_job_receipt_v1(
    *,
    tenant_id: str,
    job_id: str,
    envelope: Mapping[str, Any],
    execution_trace: Sequence[Mapping[str, Any]],
    synthesis_legality_class: str,
    synthesis_job_replay_identity: str,
    retrieval_ingress_digest: str | None,
    retrieval_subqueries: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None = None,
    claim_slots: Sequence[Mapping[str, Any]] | None = None,
    llm_invocations: Sequence[Mapping[str, Any]] | None = None,
    sd_codes_sorted: Sequence[str] | None = None,
    synthesis_degradation_rollup: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit ``synthesis_job_receipt`` with replay law fields (§Receipt)."""
    policy_digest = str(
        envelope.get("_synthesis_policy_pack_digest")
        or envelope.get("synthesis_policy_pack_digest")
        or synthesis_policy_pack_digest_v1(),
    )
    primary_rqid = primary_retrieval_query_replay_identity_v1(
        retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
    )
    receipt_embed = build_retrieval_receipt_embed_v1(
        retrieval_ingress=retrieval_ingress,
        retrieval_subqueries=retrieval_subqueries,
    )
    replay_vector = build_synthesis_job_replay_identity_vector_v1(
        envelope=envelope,
        retrieval_ingress_digest=retrieval_ingress_digest,
        retrieval_subqueries=retrieval_subqueries,
        retrieval_ingress=retrieval_ingress,
        claim_slots=claim_slots,
        llm_invocations=llm_invocations,
        sd_codes_sorted=sd_codes_sorted,
    )
    body_for_digest: dict[str, Any] = {
        "schema_version": SYNTHESIS_JOB_RECEIPT_SCHEMA_VERSION_V1,
        "tenant_id": tenant_id,
        "job_id": job_id,
        "synthesis_workload_class": envelope["synthesis_workload_class"],
        "synthesis_intent": envelope["synthesis_intent"],
        "execution_partition": envelope["execution_partition"],
        "synthesis_legality_class": synthesis_legality_class,
        "synthesis_orchestrator_build_id": SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1,
        "execution_phases": [row["phase"] for row in execution_trace if isinstance(row, Mapping)],
        "synthesis_policy_pack_digest": policy_digest,
        PHASE08_REPLAY_IDENTITY_FIELD_V1: synthesis_job_replay_identity,
        PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1: primary_rqid,
        "retrieval_subquery_replay_identities": normalize_retrieval_subquery_replay_identities_v1(
            retrieval_subqueries,
        ),
        "retrieval_ingress_digest": retrieval_ingress_digest or "",
        "claim_slot_plan_digest": replay_vector.get("claim_slot_plan_digest"),
        "prompt_hashes": replay_vector.get("prompt_hashes", []),
        "model_route_ids": replay_vector.get("model_route_ids", []),
        "sd_codes_sorted": replay_vector.get("sd_codes_sorted", []),
        "retrieval_receipt_embed_digest": receipt_embed.get("retrieval_receipt_embed_digest"),
    }
    return {
        "schema_version": SYNTHESIS_JOB_RECEIPT_SCHEMA_VERSION_V1,
        "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body_for_digest),
        "receipt_body": body_for_digest,
        "retrieval_subqueries": [dict(row) for row in retrieval_subqueries if isinstance(row, Mapping)],
        "llm_invocations": [dict(row) for row in (llm_invocations or ()) if isinstance(row, Mapping)],
        "retrieval_receipt_embed": receipt_embed,
        "synthesis_job_replay_identity_vector": replay_vector,
        "synthesis_degradation_rollup": dict(synthesis_degradation_rollup or {}),
    }


def list_recent_synthesis_jobs_replay_summary_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Recent completed jobs for replay explorer (replay identity + receipt digest only)."""
    rows = session.scalars(
        select(CortexSynthesisJob)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.status == "completed",
        )
        .order_by(CortexSynthesisJob.completed_at.desc().nullslast(), CortexSynthesisJob.created_at.desc())
        .limit(max(1, min(limit, 100))),
    ).all()
    return [
        {
            "job_id": str(row.id),
            "synthesis_job_replay_identity": row.synthesis_job_replay_identity or "",
            "receipt_digest": row.receipt_digest,
            "synthesis_legality_class": row.synthesis_legality_class,
            "synthesis_workload_class": row.synthesis_workload_class,
            "synthesis_intent": row.synthesis_intent,
        }
        for row in rows
    ]


def build_synthesis_replay_explorer_base_v1(
    *,
    tenant_id: str | None = None,
    recent_jobs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Admin replay explorer base — pin law + recent job replay identities."""
    return {
        "surface_kind": "synthesis_replay_explorer",
        "tenant_id": tenant_id or "",
        "phase08_synthesis_replay_equivalence_runtime_schema_version": (
            PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_ids": [GP08_REPLAY_01_GATE_ID_V1, GP08_REPLAY_02_GATE_ID_V1],
        "replay_identity_field": PHASE08_REPLAY_IDENTITY_FIELD_V1,
        "upstream_replay_identity_field": PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
        "replay_pin_fields": list(SYNTHESIS_REPLAY_PIN_FIELD_IDS_V1),
        "syn_rep_rules": ["SYN-REP-01", "SYN-REP-02", "SYN-REP-03", "SYN-REP-04"],
        "sd_replay_codes": [SD_REPLAY_DRIFT_V1, SD_REPLAY_TWIN_V1],
        "canonical_identity_vector_fields": [
            "synthesis_policy_pack_digest",
            "synthesis_workload_class",
            "synthesis_intent",
            "execution_partition",
            PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
            "retrieval_subquery_replay_identities",
            "retrieval_ingress_digest",
            "claim_slot_plan_digest",
            "prompt_hashes",
            "model_route_ids",
            "sd_codes_sorted",
            "synthesis_orchestrator_build_id",
        ],
        "synthesis_replay_divergence_total": get_synthesis_replay_divergence_total_v1(),
        "doctrine_anchor": PHASE08_REPLAY_EQUIVALENCE_SPEC_REF_V1,
        "twin_modes": ["inline_twin", "harness_twin", "operator_twin"],
        "recent_jobs": list(recent_jobs or ()),
    }


def build_synthesis_replay_explorer_catalog_v1(
    *,
    tenant_id: str | None = None,
    recent_jobs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Admin replay explorer — Step **17** full catalog with harness + twin schema."""
    from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
        build_synthesis_replay_explorer_catalog_v1 as _full_catalog_v1,
    )

    return _full_catalog_v1(tenant_id=tenant_id, recent_jobs=recent_jobs)


def build_synthesis_job_replay_inspector_v1(
    *,
    job_id: str,
    tenant_id: str,
    envelope_json: Mapping[str, Any],
    synthesis_job_replay_identity: str | None,
    receipt_json: Mapping[str, Any] | None,
    execution_trace: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Per-job replay inspector for admin debugger."""
    receipt = dict(receipt_json or {})
    receipt_body = receipt.get("receipt_body") if isinstance(receipt.get("receipt_body"), Mapping) else {}
    return {
        "surface_kind": "synthesis_replay_inspector",
        "tenant_id": tenant_id,
        "job_id": job_id,
        "gate_id": GP08_REPLAY_01_GATE_ID_V1,
        "synthesis_job_replay_identity": synthesis_job_replay_identity or "",
        "expected_synthesis_job_replay_identity": envelope_json.get("expected_synthesis_job_replay_identity"),
        "receipt_digest": receipt.get("receipt_digest"),
        "retrieval_receipt_embed": receipt.get("retrieval_receipt_embed"),
        "retrieval_subqueries": receipt.get("retrieval_subqueries", []),
        "synthesis_job_replay_identity_vector": receipt.get("synthesis_job_replay_identity_vector"),
        "upstream_retrieval_query_replay_identity": (
            receipt_body.get(PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1)
            if isinstance(receipt_body, Mapping)
            else None
        ),
        "execution_trace": list(execution_trace or ()),
        "replay_equivalence_twin": (
            dict(receipt.get("replay_equivalence_twin") or {})
            if isinstance(receipt, Mapping)
            else {}
        ),
        "gp08_replay_proof_passed": (
            (receipt.get("replay_equivalence_twin") or {}).get("gp08_replay_proof_passed")
            if isinstance(receipt, Mapping) and isinstance(receipt.get("replay_equivalence_twin"), Mapping)
            else None
        ),
    }


def _replay_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_REPLAY_01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_replay01_canonical_identity_stable_static() -> dict[str, Any]:
    errors: list[str] = []
    envelope = {
        "schema_version": 1,
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "synthesis_workload_class": "pipeline_default",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_pins": {"index_epoch": "epoch-1"},
        "_synthesis_policy_pack_digest": synthesis_policy_pack_digest_v1(),
    }
    subqueries = [{"retrieval_query_replay_identity": "a" * 64}]
    id1 = compute_synthesis_job_replay_identity_v1(
        envelope=envelope,
        retrieval_ingress_digest="b" * 64,
        retrieval_subqueries=subqueries,
        claim_slots=[],
    )
    id2 = compute_synthesis_job_replay_identity_v1(
        envelope=envelope,
        retrieval_ingress_digest="b" * 64,
        retrieval_subqueries=subqueries,
        claim_slots=[],
    )
    if id1 != id2:
        errors.append("identity_not_stable")
    if not _SHA256_HEX_RE.match(id1):
        errors.append("identity_not_sha256_hex")
    id3 = compute_synthesis_job_replay_identity_v1(
        envelope={**envelope, "synthesis_intent": "audit"},
        retrieval_ingress_digest="b" * 64,
        retrieval_subqueries=subqueries,
    )
    if id1 == id3:
        errors.append("intent_change_should_affect_identity")
    try:
        bad_vector = build_synthesis_job_replay_identity_vector_v1(
            envelope=envelope,
            retrieval_ingress_digest="c" * 64,
            retrieval_subqueries=subqueries,
        )
        bad_vector["llm_completion_text"] = "forbidden"
        hash_synthesis_job_replay_identity_v1(bad_vector)
    except SynthesisReplayEquivalenceError:
        pass
    else:
        errors.append("expected_forbidden_llm_key_rejection")
    return _replay_meta("gp08_replay01_canonical_identity_stable", errors)


def verify_gp08_replay01_double_run_match_static() -> dict[str, Any]:
    errors: list[str] = []
    identity = "d" * 64
    base = {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: identity,
        "synthesis_job_receipt": {"receipt_digest": "e" * 64, "retrieval_subqueries": []},
    }
    try:
        compare_gp08_replay_01_double_run_v1(base, dict(base))
    except SynthesisReplayEquivalenceError as exc:
        errors.append(f"unexpected_mismatch:{exc}")
    bad = dict(base)
    bad[PHASE08_REPLAY_IDENTITY_FIELD_V1] = "f" * 64
    try:
        compare_gp08_replay_01_double_run_v1(base, bad)
    except SynthesisReplayEquivalenceError:
        pass
    else:
        errors.append("expected_identity_mismatch")
    return _replay_meta("gp08_replay01_double_run_match", errors)


def verify_gp08_replay01_receipt_embed_law_static() -> dict[str, Any]:
    errors: list[str] = []
    embed = build_retrieval_receipt_embed_v1(
        retrieval_ingress={"retrieval_ingress_digest": "a" * 64},
        retrieval_subqueries=[{"retrieval_query_replay_identity": "b" * 64}],
    )
    if not embed.get("retrieval_receipt_embed_digest"):
        errors.append("missing_embed_digest")
    ok = verify_retrieval_receipt_embed_v1(
        embed,
        live_retrieval_response={PHASE07_REPLAY_IDENTITY_FIELD_V1: "b" * 64},
    )
    if not ok.get("passed"):
        errors.append("verify_should_pass")
    bad = verify_retrieval_receipt_embed_v1(
        embed,
        live_retrieval_response={PHASE07_REPLAY_IDENTITY_FIELD_V1: "c" * 64},
    )
    if bad.get("passed"):
        errors.append("expected_verify_failure")
    return _replay_meta("gp08_replay01_receipt_embed_law", errors)


def _replay02_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_REPLAY_02_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_replay02_publication_epoch_forward_only_static() -> dict[str, Any]:
    """``G-P08-REPLAY-02`` — publish barrier legality + forward-only epoch law (Step 32)."""
    from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
        evaluate_synthesis_publish_barrier_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_publication import (
        compare_gp08_replay02_publication_monotonicity_v1,
        verify_gp08_pub01_publication_barrier_module_static,
    )

    errors: list[str] = []
    for cls in ("synthesis_replay_safe", "synthesis_degraded"):
        barrier = evaluate_synthesis_publish_barrier_v1(synthesis_legality_class=cls)
        if not barrier.get("can_publish"):
            errors.append(f"publishable_legality_blocked:{cls}")
    forbidden = evaluate_synthesis_publish_barrier_v1(synthesis_legality_class="synthesis_forbidden")
    if forbidden.get("can_publish"):
        errors.append("forbidden_legality_must_not_publish")
    safe = evaluate_synthesis_publish_barrier_v1(synthesis_legality_class="synthesis_replay_safe")
    if safe.get("synthesis_publication_epoch") is not None:
        errors.append("materialization_barrier_must_not_pre_bump_epoch")
    if safe.get("published") is not False:
        errors.append("published_must_remain_false_pre_epoch_bump")
    pub = verify_gp08_pub01_publication_barrier_module_static()
    if not pub.get("passed"):
        errors.extend(pub.get("detail", {}).get("errors") or [])
    mono = compare_gp08_replay02_publication_monotonicity_v1(["syn-a-1", "syn-b-2"])
    if not mono.get("gp08_replay02_monotonic_passed"):
        errors.append("global_monotonic_sequence_compare_failed")
    return _replay02_meta("gp08_replay02_publication_epoch_forward_only", errors)
