"""Phase 08 P08-03 — phase boundaries vs Retrieval (07), Products (09), Admin (10).

Normative: ``DOCS/cortex/synthesis/phase-08-phase-boundaries-doctrine.md``.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
from vector.domains.cortex.synthesis.anti_goals import SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1
from vector.domains.cortex.synthesis.normative import (
    PHASE08_REPLAY_IDENTITY_FIELD_V1,
    PHASE08_SUBSTRATE_PIPELINE_STAGES_V1,
    PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
)

PHASE08_BOUNDARIES_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SD_UPSTREAM_RD_V1: Final[str] = "SD-UPSTREAM-RD"
SD_UPSTREAM_LEG_V1: Final[str] = "SD-UPSTREAM-LEG"
SD_REPLAY_TWIN_V1: Final[str] = "SD-REPLAY-TWIN"
SD_PIPELINE_GAP_V1: Final[str] = "SD-PIPELINE-GAP"

SYN_BND_RULE_IDS_V1: Final[tuple[str, ...]] = (
    "SYN-BND-07-01",
    "SYN-BND-07-02",
    "SYN-BND-07-03",
    "SYN-BND-07-04",
    "SYN-BND-07-05",
    "SYN-BND-09-01",
    "SYN-BND-09-02",
    "SYN-BND-09-03",
    "SYN-BND-10-01",
    "SYN-BND-10-02",
)

_RETRIEVAL_LEGALITY_COPY_FIELDS_V1: Final[tuple[str, ...]] = (
    "retrieval_legality_class",
    "causal_legality_class",
    "chronology_legality_class",
)

# SYN-BND-07-01 — synthesis must not bypass Phase 07 executor with smuggled fetch controls.
_FORBIDDEN_RETRIEVAL_BYPASS_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "raw_retrieval_rows",
        "sql_query",
        "direct_db_hits",
        "orm_retrieval_fetch",
        "bypass_retrieval_executor",
        "duplicate_retrieval_sql",
        "retrieval_orm_query",
    }
)

# SYN-BND-09-02/03 — product workflow fields forbidden on synthesis artifacts/jobs.
_PHASE09_PRODUCT_FIELD_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "hitl_approval",
        "product_workflow",
        "user_approval",
        "escalation_ticket",
        "deploy_action",
        "product_prompt",
        "product_template",
        "operator_escalation",
    }
)

_RD_TO_SD_PRIMARY_V1: Final[dict[str, str]] = {
    "RD-TCRE-GAP": SD_UPSTREAM_RD_V1,
    "RD-REPLAY-UNSAFE": SD_UPSTREAM_LEG_V1,
    "RD-REPLAY-TWIN": SD_REPLAY_TWIN_V1,
    "RD-INDEX-STALE": SD_PIPELINE_GAP_V1,
    "RD-LINEAGE-GAP": "SD-LINEAGE-GAP",
}

_FORBIDDEN_SYNTHESIS_IMPORT_PREFIXES_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.retrieval.query_execution",
)

_FORBIDDEN_FORWARD_IMPORT_PREFIXES_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.products",
)


class SynthesisPhaseBoundaryError(ValueError):
    """Raised when synthesis crosses Phase 07/09/10 boundaries."""

    def __init__(self, code: str, *, rule_id: str, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.rule_id = rule_id
        self.detail = dict(detail or {})
        super().__init__(f"{rule_id}:{code}")


def build_synthesis_phase_boundary_catalog_v1() -> dict[str, Any]:
    """Operator/admin catalog of SYN-BND rules (P08-03)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase08_boundaries_runtime_schema_version": int(PHASE08_BOUNDARIES_RUNTIME_SCHEMA_VERSION),
        "rule_ids": list(SYN_BND_RULE_IDS_V1),
        "acyclic_pipeline": list(PHASE08_SUBSTRATE_PIPELINE_STAGES_V1),
        "upstream_replay_identity_field": PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
        "synthesis_replay_identity_field": PHASE08_REPLAY_IDENTITY_FIELD_V1,
        "rd_to_sd_map": dict(_RD_TO_SD_PRIMARY_V1),
        "sd_upstream_rd": SD_UPSTREAM_RD_V1,
        "forbidden_retrieval_bypass_keys": sorted(_FORBIDDEN_RETRIEVAL_BYPASS_KEYS_V1),
        "phase09_forbidden_field_keys": sorted(_PHASE09_PRODUCT_FIELD_KEYS_V1),
        "rules": [
            {
                "id": "SYN-BND-07-01",
                "text": "Evidence only via execute_retrieval_query_envelope_v1 or pinned receipt bytes.",
            },
            {
                "id": "SYN-BND-07-02",
                "text": "Copy retrieval legality fields; never upgrade via LLM.",
            },
            {
                "id": "SYN-BND-07-03",
                "text": "Pin retrieval_query_replay_identity on every job and artifact header.",
            },
            {
                "id": "SYN-BND-07-04",
                "text": "Reject exploration retrieval for authoritative synthesis jobs.",
            },
            {
                "id": "SYN-BND-07-05",
                "text": "Propagate every RD-* omission to SD-* at ingress.",
            },
            {
                "id": "SYN-BND-09-01",
                "text": "Phase 09 consumes SynthesisIntelligenceArtifactV1 by id + publication epoch.",
            },
            {
                "id": "SYN-BND-09-02",
                "text": "Phase 09 owns HITL/product UX; Phase 08 provides legality + replay only.",
            },
            {
                "id": "SYN-BND-09-03",
                "text": "Product prompts live in Phase 09 templates, not Phase 08 policy pack.",
            },
            {
                "id": "SYN-BND-10-01",
                "text": "Phase 10 unifies navigation; Phase 08 ships synthesis routes with surface_kind.",
            },
            {
                "id": "SYN-BND-10-02",
                "text": "Dangerous synthesis actions follow admin dangerous-action model.",
            },
        ],
        "phase08_owns": [
            "synthesis_job_contracts",
            "evidence_constrained_intelligence",
            "llm_orchestration_law",
            "synthesis_replay_identity",
            "synthesis_receipts",
            "operator_synthesis_plane",
            "substrate_completeness_synthesis_stage",
            "pipeline_phase_08",
        ],
        "phase08_does_not_own": [
            "evidence_retrieval",
            "tcre_reconstruction",
            "graph_walks",
            "product_workflows",
            "global_admin_shell",
        ],
    }


def map_rd_code_to_sd_code_v1(rd_code: str) -> str:
    """Deterministic RD→SD propagation (doctrine § RD → SD propagation map)."""
    code = rd_code.strip()
    return _RD_TO_SD_PRIMARY_V1.get(code, SD_UPSTREAM_RD_V1)


def build_sd_row_from_rd_omission_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    """SYN-BND-07-05 — translate a retrieval omission row into an SD-* synthesis row."""
    rd_code = str(row.get("retrieval_omission_class") or row.get("rd_code") or "").strip()
    if not rd_code:
        rd_code = "RD-UNKNOWN"
    sd_code = map_rd_code_to_sd_code_v1(rd_code)
    out: dict[str, Any] = {
        "synthesis_omission_class": sd_code,
        "omission_semantics": "omitted_upstream",
        "upstream_rd": rd_code,
        "detail": dict(row.get("detail") or {}),
    }
    if sd_code == SD_UPSTREAM_RD_V1:
        out["detail"] = {**out["detail"], "rd_code": rd_code}
    return out


def propagate_retrieval_omissions_to_sd_rows_v1(
    omissions: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Build SD-* rows from Phase 07 ``retrieval_omission_rows`` / ``omissions``."""
    return [build_sd_row_from_rd_omission_v1(row) for row in (omissions or []) if isinstance(row, Mapping)]


def list_synthesis_job_retrieval_bypass_violations_v1(body: Mapping[str, Any]) -> list[str]:
    """SYN-BND-07-01 — forbid retrieval SQL/ORM bypass keys on synthesis job envelopes."""
    violations: list[str] = []
    for key in body:
        if isinstance(key, str) and key.lower() in _FORBIDDEN_RETRIEVAL_BYPASS_KEYS_V1:
            violations.append(f"{key}:forbidden_retrieval_bypass")
    return violations


def enforce_synthesis_job_retrieval_boundary_v1(body: Mapping[str, Any]) -> None:
    """Validate synthesis job envelope against Phase 07 ingress boundary."""
    hits = list_synthesis_job_retrieval_bypass_violations_v1(body)
    if hits:
        raise SynthesisPhaseBoundaryError(
            SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
            rule_id="SYN-BND-07-01",
            detail={"violations": hits},
        )


def list_synthesis_legality_upgrade_violations_v1(
    *,
    retrieval_legality_copy: Mapping[str, str],
    synthesis_legality_fields: Mapping[str, str],
) -> list[str]:
    """SYN-BND-07-02 — synthesis MUST NOT upgrade copied retrieval legality classes."""
    violations: list[str] = []
    rank = {
        "retrieval_forbidden": 0,
        "retrieval_unverifiable": 1,
        "retrieval_partial": 2,
        "retrieval_degraded": 3,
        "retrieval_replay_safe": 4,
    }
    for field in _RETRIEVAL_LEGALITY_COPY_FIELDS_V1:
        upstream = retrieval_legality_copy.get(field)
        downstream = synthesis_legality_fields.get(field)
        if upstream is None or downstream is None:
            continue
        if upstream == downstream:
            continue
        up_rank = rank.get(upstream, -1)
        down_rank = rank.get(downstream, -1)
        if down_rank > up_rank:
            violations.append(f"{field}:legality_upgrade_forbidden:{upstream}->{downstream}")
    return violations


def list_synthesis_product_field_violations_v1(body: Mapping[str, Any], *, path: str = "") -> list[str]:
    """SYN-BND-09-02/03 — product workflow fields forbidden on synthesis JSON (recursive)."""
    violations: list[str] = []
    if isinstance(body, Mapping):
        for raw_k, v in body.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{path}.{raw_k}" if path else raw_k
            if raw_k.lower() in _PHASE09_PRODUCT_FIELD_KEYS_V1:
                violations.append(f"{prefix}:phase09_product_field_forbidden")
            violations.extend(list_synthesis_product_field_violations_v1(v, path=prefix))
    elif isinstance(body, list):
        for i, item in enumerate(body):
            violations.extend(
                list_synthesis_product_field_violations_v1(item, path=f"{path}[{i}]"),
            )
    return violations


def validate_synthesis_response_no_phase09_fields_v1(body: Mapping[str, Any]) -> None:
    hits = list_synthesis_product_field_violations_v1(body)
    if hits:
        raise SynthesisPhaseBoundaryError(
            SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
            rule_id="SYN-BND-09-02",
            detail={"violations": hits[:32]},
        )


def validate_synthesis_ingress_from_retrieval_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
    job_execution_partition: str = "authoritative",
    block_authoritative_on_critical_rd: bool = True,
) -> dict[str, Any]:
    """Validate Phase 07 retrieval response before synthesis (SYN-BND-07-* + SYN-INGRESS-*)."""
    from vector.domains.cortex.synthesis.synthesis_ingress import (
        SynthesisIngressError,
        validate_retrieval_evidence_ingress_v1,
    )

    if job_envelope is not None:
        enforce_synthesis_job_retrieval_boundary_v1(job_envelope)

    try:
        ingress = validate_retrieval_evidence_ingress_v1(
            retrieval_response,
            job_envelope=job_envelope,
            job_execution_partition=job_execution_partition,
        )
    except SynthesisIngressError as exc:
        raise SynthesisPhaseBoundaryError(
            exc.code,
            rule_id=exc.gate_id,
            detail=exc.detail,
        ) from exc

    partition = str(
        job_envelope.get("execution_partition") if job_envelope is not None else job_execution_partition
    )
    sd_rows = list(ingress.get("synthesis_omission_rows") or [])
    if block_authoritative_on_critical_rd and partition.strip().lower() == "authoritative":
        critical = {SD_UPSTREAM_LEG_V1, SD_PIPELINE_GAP_V1, SD_REPLAY_TWIN_V1}
        if any(row.get("synthesis_omission_class") in critical for row in sd_rows):
            raise SynthesisPhaseBoundaryError(
                "authoritative_synthesis_blocked_on_critical_upstream_sd",
                rule_id="SYN-BND-07-05",
                detail={"synthesis_omission_rows": sd_rows[:16]},
            )

    validate_synthesis_response_no_phase09_fields_v1(retrieval_response)
    return ingress


# Re-exports for Step 03 callers — canonical implementation in ``synthesis_ingress``.
from vector.domains.cortex.synthesis.synthesis_ingress import (  # noqa: E402
    build_retrieval_evidence_ingress_v1,
    compute_retrieval_ingress_digest_v1,
    extract_retrieval_legality_copy_v1,
    list_synthesis_ingress_exploration_partition_violations_v1,
    list_synthesis_ingress_hits_violations_v1,
    list_synthesis_ingress_legality_violations_v1,
    list_synthesis_ingress_replay_identity_violations_v1,
)


def _package_py_files(root: Path, *, include_adapters: bool = False) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if not include_adapters and "adapters" in path.parts:
            continue
        if path.name == "synthesis_retrieval_client.py":
            continue
        out.append(path)
    return out


def _list_import_module_violations(
    package_dir: Path,
    *,
    forbidden_module_prefixes: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []
    for path in _package_py_files(package_dir):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path.name}:syntax_error:{exc}")
            continue
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [a.name or "" for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for mod in modules:
                for prefix in forbidden_module_prefixes:
                    if mod == prefix or mod.startswith(prefix + "."):
                        violations.append(
                            f"{path.relative_to(package_dir)}:{getattr(node, 'lineno', 0)}:import:{mod}",
                        )
    return violations


def list_synthesis_package_retrieval_bypass_import_violations_v1() -> list[str]:
    """SYN-BND-07-01 — synthesis law packages must not import retrieval query executor."""
    return _list_import_module_violations(
        Path(__file__).resolve().parent,
        forbidden_module_prefixes=_FORBIDDEN_SYNTHESIS_IMPORT_PREFIXES_V1,
    )


def list_synthesis_package_forward_product_import_violations_v1() -> list[str]:
    """Acyclic law — synthesis must not import Phase 09 product modules."""
    return _list_import_module_violations(
        Path(__file__).resolve().parent,
        forbidden_module_prefixes=_FORBIDDEN_FORWARD_IMPORT_PREFIXES_V1,
    )


def list_retrieval_package_backward_synthesis_import_violations_v1() -> list[str]:
    """Acyclic law — retrieval must not import synthesis (mirror check from SIL side)."""
    retrieval_root = Path(__file__).resolve().parents[1] / "retrieval"
    if not retrieval_root.is_dir():
        return []
    return _list_import_module_violations(
        retrieval_root,
        forbidden_module_prefixes=("vector.domains.cortex.synthesis",),
    )


def verify_gp08_bnd07_retrieval_ingress_static() -> dict[str, Any]:
    errors: list[str] = []
    legal_retrieval = {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:test",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }
    try:
        ingress = validate_synthesis_ingress_from_retrieval_v1(
            legal_retrieval,
            job_execution_partition="authoritative",
            block_authoritative_on_critical_rd=False,
        )
        if not ingress.get("retrieval_ingress_digest"):
            errors.append("missing_ingress_digest")
    except SynthesisPhaseBoundaryError as exc:
        errors.append(f"unexpected_rejection_on_legal:{exc}")

    try:
        validate_synthesis_ingress_from_retrieval_v1(
            {
                **legal_retrieval,
                "non_authoritative": True,
            },
            job_execution_partition="authoritative",
        )
    except SynthesisPhaseBoundaryError as exc:
        if exc.rule_id not in ("SYN-BND-07-04", "SYN-INGRESS-PAR-01"):
            errors.append(f"wrong_rule_id_exploration:{exc.rule_id}")
    else:
        errors.append("expected_exploration_partition_rejection")

    rows = propagate_retrieval_omissions_to_sd_rows_v1(
        [{"retrieval_omission_class": "RD-REPLAY-UNSAFE"}],
    )
    if not rows or rows[0].get("synthesis_omission_class") != SD_UPSTREAM_LEG_V1:
        errors.append("rd_replay_unsafe_sd_mapping")

    try:
        enforce_synthesis_job_retrieval_boundary_v1({"bypass_retrieval_executor": True})
    except SynthesisPhaseBoundaryError as exc:
        if exc.rule_id != "SYN-BND-07-01":
            errors.append(f"wrong_rule_id_bypass:{exc.rule_id}")
    else:
        errors.append("expected_bypass_key_rejection")

    passed = len(errors) == 0
    return {
        "id": "G-P08-BND-07",
        "name": "synthesis_retrieval_phase07_boundary",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_bnd09_products_boundary_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_synthesis_response_no_phase09_fields_v1(
            {"artifact_id": "00000000-0000-4000-8000-000000000001", "claims": []},
        )
    except SynthesisPhaseBoundaryError:
        errors.append("unexpected_rejection_on_clean_artifact")
    try:
        validate_synthesis_response_no_phase09_fields_v1({"hitl_approval": True})
    except SynthesisPhaseBoundaryError as exc:
        if exc.rule_id != "SYN-BND-09-02":
            errors.append(f"wrong_rule_id:{exc.rule_id}")
    else:
        errors.append("expected_product_field_rejection")

    upgrades = list_synthesis_legality_upgrade_violations_v1(
        retrieval_legality_copy={"retrieval_legality_class": "retrieval_degraded"},
        synthesis_legality_fields={"retrieval_legality_class": "retrieval_replay_safe"},
    )
    if not upgrades:
        errors.append("expected_legality_upgrade_detection")
    passed = len(errors) == 0
    return {
        "id": "G-P08-BND-09",
        "name": "synthesis_products_phase09_boundary",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_bnd_acyclic_dependency_static() -> dict[str, Any]:
    bypass = list_synthesis_package_retrieval_bypass_import_violations_v1()
    forward = list_synthesis_package_forward_product_import_violations_v1()
    backward = list_retrieval_package_backward_synthesis_import_violations_v1()
    errors: list[str] = []
    if bypass:
        errors.append(f"synthesis_retrieval_bypass_imports:{bypass}")
    if forward:
        errors.append(f"synthesis_forward_product_imports:{forward}")
    if backward:
        errors.append(f"retrieval_backward_synthesis_imports:{backward}")
    passed = len(errors) == 0
    return {
        "id": "G-P08-BND-ACYCLIC",
        "name": "synthesis_acyclic_pipeline_imports",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_bnd_catalog_static() -> dict[str, Any]:
    cat = build_synthesis_phase_boundary_catalog_v1()
    errors: list[str] = []
    if set(cat["rule_ids"]) != set(SYN_BND_RULE_IDS_V1):
        errors.append("rule_ids_mismatch")
    for rd in _RD_TO_SD_PRIMARY_V1:
        if rd not in RETRIEVAL_RD_CODES_REGISTRY_V1:
            errors.append(f"unregistered_rd_in_map:{rd}")
    passed = len(errors) == 0
    return {
        "id": "G-P08-BND-CATALOG",
        "name": "synthesis_boundary_catalog",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
