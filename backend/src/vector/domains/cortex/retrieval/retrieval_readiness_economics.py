"""Phase 07 P07-25 — Retrieval readiness + economics probes (mirror **P05-25** / **P06-34**).

Normative: ``DOCS/cortex/retrieval/phase-07-verification-harness-spec.md`` (**G-P07-ECO-01..03**).

Read-only probes over the shipped golden corpus manifest (**FS-RECO-01**: no mutation).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from typing import Any, Final, Literal

from vector.domains.cortex.retrieval.retrieval_addressing import retrieval_golden_vectors_v1_root

RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION: Final[int] = 1
RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1: Final[str] = "retrieval_readiness_economics_v1"
RETRIEVAL_ECONOMICS_THRESHOLD_TABLE_VERSION_V1: Final[int] = 1

GP07_ECO01_GATE_ID_V1: Final[str] = "G-P07-ECO-01"
GP07_ECO02_GATE_ID_V1: Final[str] = "G-P07-ECO-02"
GP07_ECO03_GATE_ID_V1: Final[str] = "G-P07-ECO-03"

RETRIEVAL_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/retrieval/readiness-economics",
)

ProbeProfileV1 = Literal["clean", "hostile"]


def _threshold_max_cases_for_profile_v1(profile: ProbeProfileV1) -> int:
    """Hostile profile tightens budget to force a deterministic violation if corpus is non-empty."""
    return 0 if profile == "hostile" else 64


def _golden_case_count_v1() -> int:
    root = retrieval_golden_vectors_v1_root()
    path = root / "corpus_manifest.json"
    if not path.is_file():
        return 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    cases = doc.get("cases")
    return len(cases) if isinstance(cases, list) else 0


def compute_retrieval_economics_receipt_hash_v1(stats: Mapping[str, int]) -> str:
    """Deterministic sha256 over sorted compact JSON of integer stats."""
    payload = json.dumps(dict(sorted(stats.items())), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def build_retrieval_readiness_economics_receipt_v1(
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
        violations.append("RETRIEVAL_ECO_GOLDEN_CASE_BUDGET")
    violations_sorted = sorted(violations)
    stats: dict[str, int] = {
        "golden_corpus_case_count": case_count,
        "retrieval_economics_threshold_max_cases": max_cases,
        "retrieval_economics_threshold_table_version": (
            RETRIEVAL_ECONOMICS_THRESHOLD_TABLE_VERSION_V1
        ),
        "retrieval_eco_violation_count": len(violations_sorted),
    }
    receipt_hash = compute_retrieval_economics_receipt_hash_v1(stats)
    body: dict[str, Any] = {
        "economics_receipt_hash": receipt_hash,
        "economics_stats": dict(sorted(stats.items())),
        "economics_violations": violations_sorted,
        "probe_profile": profile,
        "retrieval_readiness_economics_contract": RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1,
        "retrieval_readiness_economics_schema_version": (
            RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION
        ),
        "tenant_id": tid,
    }
    return dict(sorted(body.items()))


def verify_retrieval_readiness_economics_receipt_v1_shape(doc: Mapping[str, Any]) -> list[str]:
    errs: list[str] = []
    if doc.get("retrieval_readiness_economics_contract") != RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1:
        errs.append("contract_mismatch")
    if doc.get("retrieval_readiness_economics_schema_version") != (
        RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION
    ):
        errs.append("schema_version_mismatch")
    if not isinstance(doc.get("economics_receipt_hash"), str):
        errs.append("missing_receipt_hash")
    stats = doc.get("economics_stats")
    if not isinstance(stats, dict):
        errs.append("economics_stats_not_object")
    return errs


def _eco_gate(gate_id: str, name: str, passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": passed,
        "severity": "hard_fail",
        "detail": dict(detail),
    }


def verify_gp07_eco01_readiness_economics_clean_profile_static() -> dict[str, Any]:
    """**G-P07-ECO-01** — clean profile admits shipped golden corpus size."""
    body = build_retrieval_readiness_economics_receipt_v1(
        tenant_id=uuid.UUID(int=0),
        profile="clean",
    )
    shape_errs = verify_retrieval_readiness_economics_receipt_v1_shape(body)
    passed = body.get("economics_violations") == [] and not shape_errs
    return _eco_gate(
        GP07_ECO01_GATE_ID_V1,
        "retrieval_readiness_economics_clean_profile",
        passed,
        {"underlying": body, "shape_errors": shape_errs},
    )


def verify_gp07_eco02_readiness_economics_hostile_profile_static() -> dict[str, Any]:
    """**G-P07-ECO-02** — hostile profile: deterministic budget violation when corpus is non-empty."""
    body = build_retrieval_readiness_economics_receipt_v1(
        tenant_id=uuid.UUID(int=0),
        profile="hostile",
    )
    passed = body.get("economics_violations") == ["RETRIEVAL_ECO_GOLDEN_CASE_BUDGET"]
    return _eco_gate(
        GP07_ECO02_GATE_ID_V1,
        "retrieval_readiness_economics_hostile_profile",
        passed,
        {"underlying": body},
    )


def verify_gp07_eco03_admin_openapi_path_matrix_static() -> dict[str, Any]:
    """**G-P07-ECO-03** — readiness economics admin OpenAPI path matrix."""
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/retrieval/readiness-economics",)
    if RETRIEVAL_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in RETRIEVAL_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/retrieval/readiness-economics" not in p:
            errors.append(f"path_missing_economics_segment:{p}")
    return _eco_gate(
        GP07_ECO03_GATE_ID_V1,
        "retrieval_readiness_economics_admin_openapi_path_matrix",
        len(errors) == 0,
        {"errors": errors},
    )
