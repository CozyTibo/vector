"""Phase 08 Step 12 — prompt assembly law (**SYN-PRM-***, **G-P08-PRM-01**)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
    GP08_PRM01_GATE_ID_V1,
    SynthesisPromptAssemblyError,
    assemble_synthesis_prompts_for_job_v1,
    build_synthesis_prompt_assembly_preview_v1,
    build_synthesis_prompt_context_v1,
    build_synthesis_prompt_template_catalog_v1,
    compute_synthesis_prompt_hash_v1,
    load_synthesis_prompt_template_v1,
    resolve_template_variant_id_v1,
    verify_gp08_prm01_context_required_fields_static,
    verify_gp08_prm01_prompt_hash_stable_static,
    verify_gp08_prm01_template_registry_static,
    verify_gp08_prm01_variant_override_law_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8prm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 PRM User")
    tenant = Tenant(
        company_name="P8PRM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8prm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _minimal_envelope(tenant_id: uuid.UUID) -> dict[str, object]:
    return {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
    }


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-prm",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


@pytest.mark.parametrize(
    "verifier",
    [
        verify_gp08_prm01_template_registry_static,
        verify_gp08_prm01_prompt_hash_stable_static,
        verify_gp08_prm01_context_required_fields_static,
        verify_gp08_prm01_variant_override_law_static,
    ],
)
def test_gp08_prm01_static_gates(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["id"] == GP08_PRM01_GATE_ID_V1
    assert out["passed"] is True


def test_prompt_template_catalog_lists_struct_default() -> None:
    cat = build_synthesis_prompt_template_catalog_v1()
    assert cat["gate_id"] == GP08_PRM01_GATE_ID_V1
    ids = {t["prompt_template_id"] for t in cat["prompt_templates"]}
    assert "synthesis_struct_default" in ids


def test_prompt_hash_stable_and_64_hex() -> None:
    ctx = build_synthesis_prompt_context_v1(
        envelope={"synthesis_workload_class": "degradation_brief", "synthesis_intent": "inspect"},
        claim_slots=[],
        synthesis_omission_rows=[],
        retrieval_ingress={"retrieval_evidence_hits": []},
    )
    a = compute_synthesis_prompt_hash_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
        context=ctx,
        template_variant_id="default",
    )
    b = compute_synthesis_prompt_hash_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
        context=ctx,
        template_variant_id="default",
    )
    assert a == b
    assert len(a) == 64


def test_variant_override_changes_hash() -> None:
    template = load_synthesis_prompt_template_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
    )
    env = {
        "synthesis_prompt_overrides": {"synthesis_struct_default": "variant_pin_a"},
    }
    v_default = resolve_template_variant_id_v1(
        prompt_template_id="synthesis_struct_default",
        template=template,
        envelope={},
    )
    v_pin = resolve_template_variant_id_v1(
        prompt_template_id="synthesis_struct_default",
        template=template,
        envelope=env,
    )
    assert v_default == "default"
    assert v_pin == "variant_pin_a"
    ctx: dict[str, Any] = build_synthesis_prompt_context_v1(
        envelope=env,
        claim_slots=[],
        synthesis_omission_rows=[],
        retrieval_ingress=None,
    )
    h0 = compute_synthesis_prompt_hash_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
        context=ctx,
        template_variant_id=v_default,
    )
    h1 = compute_synthesis_prompt_hash_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
        context=ctx,
        template_variant_id=v_pin,
    )
    assert h0 != h1


def test_invalid_variant_rejected() -> None:
    template = load_synthesis_prompt_template_v1(
        prompt_template_id="synthesis_struct_default",
        prompt_template_version=1,
    )
    with pytest.raises(SynthesisPromptAssemblyError, match="invalid_template_variant_override"):
        resolve_template_variant_id_v1(
            prompt_template_id="synthesis_struct_default",
            template=template,
            envelope={
                "synthesis_prompt_overrides": {
                    "synthesis_struct_default": "not_registered",
                },
            },
        )


def test_orchestrator_assemble_phase_emits_prompt_hashes(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    assemble_row = next(row for row in out["execution_trace"] if row["phase"] == "ASSEMBLE")
    assert assemble_row.get("prompt_assembly_count", 0) >= 1
    assert len(assemble_row.get("prompt_hashes") or []) >= 1
    assert len(out.get("prompt_hashes") or []) >= 1
    assert out["prompt_hashes"] == assemble_row["prompt_hashes"]
    receipt = out["synthesis_job_receipt"]
    assert len(receipt.get("prompt_assemblies") or []) >= 1


def test_admin_style_preview_surface() -> None:
    raw = build_synthesis_prompt_assembly_preview_v1(
        {
            "schema_version": 1,
            "tenant_id": str(uuid.UUID(int=0)),
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        claim_slots=[],
    )
    assert raw["surface_kind"] == "synthesis_prompt_assembly_preview"
    assert raw["gate_id"] == GP08_PRM01_GATE_ID_V1
    assert raw["prompt_assembly_count"] >= 1


def test_assemble_job_matches_preview_hash() -> None:
    env = {
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
    }
    preview = build_synthesis_prompt_assembly_preview_v1(env, claim_slots=[])
    job_assemblies = assemble_synthesis_prompts_for_job_v1(
        envelope=env,
        claim_slots=[],
        synthesis_omission_rows=[],
        retrieval_ingress={"retrieval_evidence_hits": []},
    )
    assert sorted(preview["prompt_hashes"]) == sorted(
        str(a["prompt_hash"]) for a in job_assemblies if a.get("prompt_hash")
    )
