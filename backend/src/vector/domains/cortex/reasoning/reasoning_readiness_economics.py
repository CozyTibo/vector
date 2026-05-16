"""Phase 06 P06-34 — Reasoning readiness + economics probes (mirror **P05-25** intent).

Normative: ``DOCS/cortex/reasoning/reasoning-verification-harness-spec.md``;
``DOCS/cortex/reasoning/reasoning-admin-control-plane-spec.md`` (replay pressure / economics).

Read-only probes over the shipped **golden-thread** corpus manifest (**FS-RECO-01**: no mutation).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from typing import Any, Final, Literal

from vector.domains.cortex.reasoning.reasoning_golden_thread_binding import (
    load_reasoning_corpus_manifest_v1,
    reasoning_golden_vectors_v1_root,
)

REASONING_READINESS_ECONOMICS_SCHEMA_VERSION: Final[int] = 1
REASONING_READINESS_ECONOMICS_CONTRACT_V1: Final[str] = "reasoning_readiness_economics_v1"
REASONING_ECONOMICS_THRESHOLD_TABLE_VERSION_V1: Final[int] = 1

REASONING_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/reasoning/readiness-economics",
)

ProbeProfileV1 = Literal["clean", "hostile"]


def _threshold_max_cases_for_profile_v1(profile: ProbeProfileV1) -> int:
    """Hostile profile tightens budget to force a deterministic violation if corpus is non-empty."""
    return 0 if profile == "hostile" else 64


def _golden_case_count_v1() -> int:
    root = reasoning_golden_vectors_v1_root()
    doc = load_reasoning_corpus_manifest_v1(root / "corpus_manifest.json")
    cases = doc.get("cases")
    return len(cases) if isinstance(cases, list) else 0


def compute_reasoning_economics_receipt_hash_v1(stats: Mapping[str, int]) -> str:
    """Deterministic sha256 over sorted compact JSON of integer stats."""
    payload = json.dumps(dict(sorted(stats.items())), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def build_reasoning_readiness_economics_receipt_v1(
    *,
    tenant_id: uuid.UUID | str,
    profile: ProbeProfileV1 = "clean",
) -> dict[str, Any]:
    """Numeric readiness / economics receipt (**read-only** golden manifest probes)."""
    tid = str(tenant_id)
    case_count = int(_golden_case_count_v1())
    max_cases = _threshold_max_cases_for_profile_v1(profile)
    violations: list[str] = []
    if case_count > max_cases:
        violations.append("REASONING_ECO_GOLDEN_CASE_BUDGET")
    violations_sorted = sorted(violations)
    stats: dict[str, int] = {
        "golden_corpus_case_count": case_count,
        "reasoning_economics_threshold_max_cases": max_cases,
        "reasoning_economics_threshold_table_version": (
            REASONING_ECONOMICS_THRESHOLD_TABLE_VERSION_V1
        ),
        "reasoning_eco_violation_count": len(violations_sorted),
    }
    receipt_hash = compute_reasoning_economics_receipt_hash_v1(stats)
    body: dict[str, Any] = {
        "economics_receipt_hash": receipt_hash,
        "economics_stats": dict(sorted(stats.items())),
        "economics_violations": violations_sorted,
        "probe_profile": profile,
        "reasoning_readiness_economics_contract": REASONING_READINESS_ECONOMICS_CONTRACT_V1,
        "reasoning_readiness_economics_schema_version": (
            REASONING_READINESS_ECONOMICS_SCHEMA_VERSION
        ),
        "tenant_id": tid,
    }
    return dict(sorted(body.items()))


def verify_gp06_rreco01_readiness_economics_clean_profile_static() -> dict[str, Any]:
    """Clean profile: non-hostile thresholds admit the shipped golden corpus size."""
    body = build_reasoning_readiness_economics_receipt_v1(
        tenant_id=uuid.UUID(int=0),
        profile="clean",
    )
    passed = body.get("economics_violations") == []
    return {
        "id": "P06-34-rreco-clean",
        "name": "reasoning_readiness_economics_clean_profile",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"underlying": body},
    }


def verify_gp06_rreco02_readiness_economics_hostile_profile_static() -> dict[str, Any]:
    """Hostile profile: deterministic budget violation when corpus is non-empty."""
    body = build_reasoning_readiness_economics_receipt_v1(
        tenant_id=uuid.UUID(int=0),
        profile="hostile",
    )
    passed = body.get("economics_violations") == ["REASONING_ECO_GOLDEN_CASE_BUDGET"]
    return {
        "id": "P06-34-rreco-hostile",
        "name": "reasoning_readiness_economics_hostile_profile",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"underlying": body},
    }


def verify_gp06_rreco03_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/reasoning/readiness-economics",)
    if REASONING_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in REASONING_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/reasoning/readiness-economics" not in p:
            errors.append(f"path_missing_economics_segment:{p}")
    return {
        "id": "P06-34-rreco-paths",
        "name": "reasoning_readiness_economics_admin_openapi_path_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
