"""Phase 07 P07-03 — phase boundaries vs TCRE (06), Synthesis (08), Products (09).

Normative: ``DOCS/cortex/retrieval/phase-07-phase-boundaries-doctrine.md``.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.retrieval.anti_goals import (
    RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
    list_retrieval_forbidden_cognition_key_violations,
)
from vector.domains.cortex.retrieval.normative import PHASE07_SUBSTRATE_PIPELINE_STAGES_V1

PHASE07_BOUNDARIES_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_RD_TCRE_GAP_V1: Final[str] = "RD-TCRE-GAP"

# RET-BND-06 handoff keys (Phase 06 RUNTIME-02 → Phase 07 index).
TCRE_RETRIEVAL_HANDOFF_REF_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_lookup_id",
        "retrieval_chain_ref",
        "chronology_window_ref",
    }
)

# RET-BND-08-02 — synthesis-shaped fields forbidden on retrieval responses.
PHASE08_SYNTHESIS_FORBIDDEN_RESPONSE_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "answer",
        "answers",
        "summary",
        "summaries",
        "bullets",
        "bullet_points",
        "recommendation",
        "recommendations",
        "narrative",
        "narratives",
        "synthesis",
        "synthesis_output",
    }
)

# RET-BND-06-01 — retrieval MUST NOT invoke inline TCRE reducer/rebuild controls.
_FORBIDDEN_TCRE_REDUCER_INVOCATION_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "invoke_tcre_reducer",
        "rebuild_causal_chain",
        "recompute_chronology",
        "run_tcre_job",
        "run_tcre_reconstruction",
        "tcre_reducer_invocation",
    }
)

RET_BND_RULE_IDS_V1: Final[tuple[str, ...]] = (
    "RET-BND-06-01",
    "RET-BND-06-02",
    "RET-BND-06-03",
    "RET-BND-08-01",
    "RET-BND-08-02",
    "RET-BND-08-03",
    "RET-BND-09-01",
    "RET-BND-09-02",
)

RETRIEVAL_RD_CODES_V1: Final[frozenset[str]] = frozenset(
    {
        "RD-CAP-HITS",
        "RD-CAP-CHRON",
        "RD-CAP-EDGE",
        "RD-CAP-LINEAGE",
        "RD-TCRE-GAP",
        "RD-GRAPH-ORPHAN",
        "RD-TRAVERSAL-IDLE",
        "RD-TRAVERSAL-BLOCKED",
        "RD-LINEAGE-GAP",
        "RD-REPLAY-UNSAFE",
        "RD-INDEX-STALE",
        "RD-POLICY-MISMATCH",
        "RD-ADDRESSING-UNRESOLVED",
    }
)

_UPSTREAM_TCRE_GAP_TRIGGER_V1: Final[str] = "reconstruction_coverage_gap"

_FORBIDDEN_RETRIEVAL_IMPORT_ROOTS_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.synthesis",
)

_FORBIDDEN_REASONING_IMPORT_OF_RETRIEVAL_V1: Final[str] = "vector.domains.cortex.retrieval"


class RetrievalPhaseBoundaryError(ValueError):
    """Raised when retrieval crosses Phase 06/08/09 boundaries."""

    def __init__(self, code: str, *, rule_id: str, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.rule_id = rule_id
        self.detail = dict(detail or {})
        super().__init__(f"{rule_id}:{code}")


def build_retrieval_phase_boundary_catalog_v1() -> dict[str, Any]:
    """Operator/admin catalog of RET-BND rules (P07-03)."""
    return {
        "phase07_boundaries_runtime_schema_version": PHASE07_BOUNDARIES_RUNTIME_SCHEMA_VERSION,
        "rule_ids": list(RET_BND_RULE_IDS_V1),
        "acyclic_pipeline": list(PHASE07_SUBSTRATE_PIPELINE_STAGES_V1) + ["Synthesis", "Products"],
        "tcre_handoff_ref_keys": sorted(TCRE_RETRIEVAL_HANDOFF_REF_KEYS_V1),
        "rd_tcre_gap_code": RETRIEVAL_RD_TCRE_GAP_V1,
        "phase08_forbidden_response_keys": sorted(PHASE08_SYNTHESIS_FORBIDDEN_RESPONSE_KEYS_V1),
        "rules": [
            {
                "id": "RET-BND-06-01",
                "text": "Read TCRE artifacts as stored; no inline reducer invocation except replay-pinned workloads.",
            },
            {
                "id": "RET-BND-06-02",
                "text": "Copy chronology/causal legality from upstream; no re-projection without policy_override_exploration.",
            },
            {
                "id": "RET-BND-06-03",
                "text": "Surface reconstruction_coverage_gap as RD-TCRE-GAP — never empty success.",
            },
            {
                "id": "RET-BND-08-01",
                "text": "Phase 08 must consume RetrievalEvidenceHitV1 + query receipt only.",
            },
            {
                "id": "RET-BND-08-02",
                "text": "Retrieval must not return synthesis-shaped fields.",
            },
            {
                "id": "RET-BND-08-03",
                "text": "Exploration partition responses require non_authoritative: true.",
            },
            {
                "id": "RET-BND-09-01",
                "text": "Phase 09 orchestrates calls; retrieval does not encode product UX.",
            },
            {
                "id": "RET-BND-09-02",
                "text": "HITL approvals live in Phase 09; retrieval provides audit + replay identity only.",
            },
        ],
        "phase07_owns": [
            "query_contracts",
            "addressing",
            "evidence_access",
            "provenance_surfacing",
            "temporal_scopes",
            "index_law",
            "operator_visibility",
            "substrate_completeness",
        ],
        "phase07_does_not_own": [
            "tcre_reconstruction_jobs",
            "octs_walks",
            "org_link_authority",
            "canonical_transform",
            "raw_exhaust_ingest",
            "synthesis",
            "operational_products",
            "cross_phase_admin_shell",
        ],
    }


def map_upstream_trigger_to_rd_code_v1(trigger: str) -> str | None:
    """Map substrate/TCRE omission triggers to closed ``RD-*`` codes."""
    from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
        map_upstream_trigger_to_rd_code_v1 as _map_v1,
    )

    mapped = _map_v1(trigger)
    if mapped is not None:
        return mapped
    if trigger.strip() == _UPSTREAM_TCRE_GAP_TRIGGER_V1:
        return RETRIEVAL_RD_TCRE_GAP_V1
    return None


def build_rd_tcre_gap_omission_row_v1(
    *,
    trigger: str = _UPSTREAM_TCRE_GAP_TRIGGER_V1,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """RET-BND-06-03 — lawful omission row for TCRE coverage gaps."""
    return {
        "retrieval_omission_class": RETRIEVAL_RD_TCRE_GAP_V1,
        "upstream_trigger": trigger,
        "detail": dict(detail or {}),
    }


def list_retrieval_envelope_tcre_reducer_violations_v1(body: Mapping[str, Any]) -> list[str]:
    """RET-BND-06-01 — forbid inline TCRE reducer invocation on retrieval envelopes."""
    violations: list[str] = []
    for key in body:
        if isinstance(key, str) and key.lower() in _FORBIDDEN_TCRE_REDUCER_INVOCATION_KEYS_V1:
            violations.append(f"{key}:forbidden_tcre_reducer_invocation")
    return violations


def enforce_retrieval_envelope_phase06_boundary_v1(body: Mapping[str, Any]) -> None:
    """Validate query envelope against Phase 06 boundary (RET-BND-06-01)."""
    hits = list_retrieval_envelope_tcre_reducer_violations_v1(body)
    if hits:
        raise RetrievalPhaseBoundaryError(
            RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
            rule_id="RET-BND-06-01",
            detail={"violations": hits},
        )


def list_retrieval_hit_legality_reprojection_violations_v1(
    hit: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
    policy_override_exploration: bool = False,
) -> list[str]:
    """RET-BND-06-02 — legality classes must be copied from upstream unless exploration override."""
    if execution_partition.strip().lower() == "exploration" and policy_override_exploration:
        return []
    violations: list[str] = []
    for field, upstream_field in (
        ("chronology_legality_class", "upstream_chronology_legality_class"),
        ("causal_legality_class", "upstream_causal_legality_class"),
    ):
        if field not in hit:
            continue
        if upstream_field not in hit:
            violations.append(f"{field}:missing_upstream_copy_source")
            continue
        if hit[field] != hit[upstream_field]:
            violations.append(f"{field}:reprojected_without_exploration_override")
    return violations


def validate_retrieval_hit_legality_copy_from_upstream_v1(
    hit: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
    policy_override_exploration: bool = False,
) -> None:
    hits = list_retrieval_hit_legality_reprojection_violations_v1(
        hit,
        execution_partition=execution_partition,
        policy_override_exploration=policy_override_exploration,
    )
    if hits:
        raise RetrievalPhaseBoundaryError(
            "retrieval_legality_reprojection_forbidden",
            rule_id="RET-BND-06-02",
            detail={"violations": hits},
        )


def list_retrieval_synthesis_field_violations_v1(body: Mapping[str, Any], *, path: str = "") -> list[str]:
    """RET-BND-08-02 — synthesis-shaped keys forbidden (recursive)."""
    violations: list[str] = []
    if isinstance(body, Mapping):
        for raw_k, v in body.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{path}.{raw_k}" if path else raw_k
            if raw_k.lower() in PHASE08_SYNTHESIS_FORBIDDEN_RESPONSE_KEYS_V1:
                violations.append(f"{prefix}:phase08_synthesis_field_forbidden")
            violations.extend(list_retrieval_synthesis_field_violations_v1(v, path=prefix))
    elif isinstance(body, list):
        for i, item in enumerate(body):
            violations.extend(
                list_retrieval_synthesis_field_violations_v1(item, path=f"{path}[{i}]")
            )
    return violations


def validate_retrieval_response_no_phase08_fields_v1(body: Mapping[str, Any]) -> None:
    hits = list_retrieval_synthesis_field_violations_v1(body)
    if hits:
        raise RetrievalPhaseBoundaryError(
            RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
            rule_id="RET-BND-08-02",
            detail={"violations": hits},
        )


def validate_retrieval_exploration_partition_label_v1(
    body: Mapping[str, Any],
    *,
    execution_partition: str,
) -> None:
    """RET-BND-08-03 — exploration partition requires ``non_authoritative: true``."""
    if execution_partition.strip().lower() != "exploration":
        return
    if body.get("non_authoritative") is not True:
        raise RetrievalPhaseBoundaryError(
            "exploration_partition_requires_non_authoritative_label",
            rule_id="RET-BND-08-03",
            detail={"execution_partition": execution_partition},
        )


def list_retrieval_silent_tcre_gap_violations_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    hits: list[Any] | None,
    omissions: list[Mapping[str, Any]] | None,
) -> list[str]:
    """RET-BND-06-03 — TCRE gap must not yield empty success without RD-TCRE-GAP."""
    triggers = dict(upstream_triggers or {})
    if not triggers.get(_UPSTREAM_TCRE_GAP_TRIGGER_V1):
        return []
    if hits:
        return []
    rd_codes = {
        str(o.get("retrieval_omission_class") or o.get("rd_code") or "")
        for o in (omissions or [])
    }
    if RETRIEVAL_RD_TCRE_GAP_V1 in rd_codes:
        return []
    return ["silent_tcre_coverage_gap:missing_RD-TCRE-GAP_omission"]


def validate_retrieval_result_no_silent_tcre_gap_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    hits: list[Any] | None,
    omissions: list[Mapping[str, Any]] | None,
) -> None:
    hits_v = list_retrieval_silent_tcre_gap_violations_v1(
        upstream_triggers=upstream_triggers, hits=hits, omissions=omissions
    )
    if hits_v:
        raise RetrievalPhaseBoundaryError(
            "silent_tcre_coverage_gap",
            rule_id="RET-BND-06-03",
            detail={"violations": hits_v},
        )


def merge_upstream_triggers_into_retrieval_omissions_v1(
    upstream_triggers: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build omission rows from upstream substrate triggers (RET-BND-06-03 propagation)."""
    from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
        propagate_upstream_triggers_to_rd_omissions_v1,
    )

    return propagate_upstream_triggers_to_rd_omissions_v1(upstream_triggers)


def validate_retrieval_response_phase_boundaries_v1(
    body: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
    upstream_triggers: Mapping[str, Any] | None = None,
    policy_override_exploration: bool = False,
) -> None:
    """Apply RET-BND-06/08 boundary validators to a retrieval response body."""
    validate_retrieval_response_no_phase08_fields_v1(body)
    validate_retrieval_exploration_partition_label_v1(
        body, execution_partition=execution_partition
    )
    cognition = list_retrieval_forbidden_cognition_key_violations(body)
    if cognition:
        raise RetrievalPhaseBoundaryError(
            RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
            rule_id="RET-BND-08-02",
            detail={"cognition_violations": cognition[:16]},
        )
    hit_list = body.get("hits")
    if isinstance(hit_list, list):
        for i, hit in enumerate(hit_list):
            if isinstance(hit, Mapping):
                validate_retrieval_hit_legality_copy_from_upstream_v1(
                    hit,
                    execution_partition=execution_partition,
                    policy_override_exploration=policy_override_exploration,
                )
    omissions_raw = body.get("omissions") or body.get("retrieval_omission_rows")
    omissions = [o for o in omissions_raw if isinstance(o, Mapping)] if isinstance(
        omissions_raw, list
    ) else []
    validate_retrieval_result_no_silent_tcre_gap_v1(
        upstream_triggers=upstream_triggers,
        hits=hit_list if isinstance(hit_list, list) else None,
        omissions=omissions,
    )


def _package_py_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
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
                            f"{path.relative_to(package_dir)}:{getattr(node, 'lineno', 0)}:import:{mod}"
                        )
    return violations


def list_retrieval_package_forward_phase_import_violations_v1() -> list[str]:
    """Acyclic law — retrieval must not import Phase 08 synthesis modules."""
    return _list_import_module_violations(
        Path(__file__).resolve().parent,
        forbidden_module_prefixes=_FORBIDDEN_RETRIEVAL_IMPORT_ROOTS_V1,
    )


def list_reasoning_package_retrieval_import_violations_v1() -> list[str]:
    """Acyclic law — TCRE (Phase 06) must not import retrieval for reconstruction."""
    reasoning_root = Path(__file__).resolve().parents[1] / "reasoning"
    if not reasoning_root.is_dir():
        return []
    return _list_import_module_violations(
        reasoning_root,
        forbidden_module_prefixes=(_FORBIDDEN_REASONING_IMPORT_OF_RETRIEVAL_V1,),
    )


def verify_gp07_bnd06_tcre_boundary_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        enforce_retrieval_envelope_phase06_boundary_v1({"workload_class": "causal_chain"})
    except RetrievalPhaseBoundaryError:
        errors.append("unexpected_rejection_on_clean_envelope")
    try:
        enforce_retrieval_envelope_phase06_boundary_v1(
            {"workload_class": "causal_chain", "run_tcre_reconstruction": True}
        )
    except RetrievalPhaseBoundaryError:
        pass
    else:
        errors.append("expected_rejection_for_run_tcre_reconstruction")
    gap_row = build_rd_tcre_gap_omission_row_v1()
    if gap_row.get("retrieval_omission_class") != RETRIEVAL_RD_TCRE_GAP_V1:
        errors.append("rd_tcre_gap_row_shape")
    try:
        validate_retrieval_result_no_silent_tcre_gap_v1(
            upstream_triggers={_UPSTREAM_TCRE_GAP_TRIGGER_V1: True},
            hits=[],
            omissions=[],
        )
    except RetrievalPhaseBoundaryError as exc:
        if exc.rule_id != "RET-BND-06-03":
            errors.append(f"wrong_rule_id:{exc.rule_id}")
    else:
        errors.append("expected_silent_gap_rejection")
    passed = len(errors) == 0
    return {
        "id": "G-P07-BND-06",
        "name": "retrieval_tcre_phase06_boundary",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_bnd08_synthesis_boundary_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_retrieval_response_no_phase08_fields_v1({"retrieval_lookup_id": "x"})
    except RetrievalPhaseBoundaryError:
        errors.append("unexpected_rejection_on_clean_response")
    try:
        validate_retrieval_response_no_phase08_fields_v1({"answer": "no"})
    except RetrievalPhaseBoundaryError as exc:
        if exc.rule_id != "RET-BND-08-02":
            errors.append(f"wrong_rule_id:{exc.rule_id}")
    else:
        errors.append("expected_rejection_for_answer_field")
    try:
        validate_retrieval_exploration_partition_label_v1(
            {"retrieval_lookup_id": "x"}, execution_partition="exploration"
        )
    except RetrievalPhaseBoundaryError:
        pass
    else:
        errors.append("expected_exploration_label_requirement")
    try:
        validate_retrieval_exploration_partition_label_v1(
            {"retrieval_lookup_id": "x", "non_authoritative": True},
            execution_partition="exploration",
        )
    except RetrievalPhaseBoundaryError:
        errors.append("unexpected_rejection_on_labeled_exploration")
    passed = len(errors) == 0
    return {
        "id": "G-P07-BND-08",
        "name": "retrieval_synthesis_phase08_boundary",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_bnd_acyclic_dependency_static() -> dict[str, Any]:
    fwd = list_retrieval_package_forward_phase_import_violations_v1()
    back = list_reasoning_package_retrieval_import_violations_v1()
    errors: list[str] = []
    if fwd:
        errors.append(f"retrieval_forward_imports:{fwd}")
    if back:
        errors.append(f"reasoning_backward_retrieval_imports:{back}")
    passed = len(errors) == 0
    return {
        "id": "G-P07-BND-ACYCLIC",
        "name": "retrieval_acyclic_pipeline_imports",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_bnd_catalog_static() -> dict[str, Any]:
    cat = build_retrieval_phase_boundary_catalog_v1()
    errors: list[str] = []
    if set(cat["rule_ids"]) != set(RET_BND_RULE_IDS_V1):
        errors.append("rule_ids_mismatch")
    if RETRIEVAL_RD_TCRE_GAP_V1 not in RETRIEVAL_RD_CODES_V1:
        errors.append("rd_tcre_gap_not_in_registry")
    passed = len(errors) == 0
    return {
        "id": "G-P07-BND-CATALOG",
        "name": "retrieval_boundary_catalog",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
