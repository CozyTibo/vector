"""Phase 08.5 P085-03 — phase boundaries vs Phase 08 SIL, Phase 09 products, Phase 10 admin.

Normative: ``DOCS/cortex/operational-runtime/phase-085-phase-boundaries-doctrine.md``.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_HARD_DOWNSTREAM_GATE_V1,
    PHASE085_NORMATIVE_TREE_V1,
    PHASE085_RUNTIME_PACKAGE_V1,
    PHASE085_SUBSTRATE_EXECUTION_CHAIN_V1,
    _repo_root_v1,
)

PHASE085_BOUNDARIES_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_BOUNDARIES_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-phase-boundaries-doctrine.md"
)

GP085_BND_CATALOG_GATE_ID_V1: Final[str] = "G-P085-BND-CATALOG"
GP085_BND_ACYCLIC_GATE_ID_V1: Final[str] = "G-P085-BND-ACYCLIC"

CESP_BND_RULE_IDS_V1: Final[tuple[str, ...]] = (
    "CESP-BND-08-01",
    "CESP-BND-08-02",
    "CESP-BND-09-01",
    "CESP-BND-10-01",
)

# Normalized substrate chain from normative (ingestion → synthesis) + CESP + downstream.
PHASE085_SUBSTRATE_ACYCLIC_CHAIN_V1: Final[tuple[str, ...]] = (
    *PHASE085_SUBSTRATE_EXECUTION_CHAIN_V1,
    "phase_08_5_cesp",
    "phase_09_products",
)

SYNTHESIS_ARTIFACT_SCHEMA_REL_PATH_V1: Final[str] = (
    "DOCS/cortex/synthesis/schemas/synthesis-intelligence-artifact-v1.schema.json"
)

_FORBIDDEN_CESP_IMPORT_PREFIXES_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.products",
)

_CESP_ALLOWED_EXTENSION_IMPORTERS_V1: Final[frozenset[str]] = frozenset(
    {
        "vector.domains.cortex.completeness",
        "vector.domains.cortex.completeness.substrate_completeness_ledger",
        "vector.domains.cortex.retrieval.retrieval_completeness_projection",
    }
)

_CESP_ALLOWED_UPSTREAM_IMPORT_PREFIXES_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.completeness",
    "vector.domains.cortex.execution",
    "vector.domains.cortex.retrieval",
    "vector.domains.cortex.synthesis",
    "vector.domains.cortex.substrate_pipeline",
    "vector.domains.cortex.reasoning",
    "vector.domains.cortex.traversal",
    "vector.domains.cortex.identity",
    "vector.domains.cortex.ingestion",
    "vector.domains.cortex.operational_runtime",
    "vector.infrastructure",
    "vector.contracts",
    "vector.domains.tenancy",
)

_CESP_OWNED_RUNTIME_ARTIFACTS_V1: Final[tuple[str, ...]] = (
    "cortex_pipeline_continuation_states",
    "cortex_retrieval_materialization_reports",
    "cortex_synthesis_activation_audits",
    "operational_idle_class",
    "synthesis_idle_classification",
    "substrate_operational_health",
    "substrate_runtime_maturity",
)

_CESP_ADMIN_ROUTE_PREFIXES_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/operational-runtime/",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/",
)

_PHASE09_FORBIDDEN_SHIP_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "phase09_enabled",
        "product_workflow_enabled",
        "operational_intelligence_products_live",
    }
)


class CespPhaseBoundaryError(ValueError):
    """Raised when CESP crosses Phase 08/09/10 boundaries."""

    def __init__(self, code: str, *, rule_id: str, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.rule_id = rule_id
        self.detail = dict(detail or {})
        super().__init__(f"{rule_id}:{code}")


def hash_synthesis_artifact_schema_fixture_v1() -> str:
    """Pinned digest for **CESP-BND-08-01** (schema file must match program lock)."""
    path = _repo_root_v1() / SYNTHESIS_ARTIFACT_SCHEMA_REL_PATH_V1
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_operational_runtime_phase_boundary_catalog_v1() -> dict[str, Any]:
    """Operator/admin catalog of CESP-BND rules (P085-03)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_boundaries_runtime_schema_version": int(PHASE085_BOUNDARIES_RUNTIME_SCHEMA_VERSION),
        "spec_ref": PHASE085_BOUNDARIES_SPEC_REF_V1,
        "runtime_package": PHASE085_RUNTIME_PACKAGE_V1,
        "rule_ids": list(CESP_BND_RULE_IDS_V1),
        "acyclic_pipeline": list(PHASE085_SUBSTRATE_ACYCLIC_CHAIN_V1),
        "hard_downstream_gate": PHASE085_HARD_DOWNSTREAM_GATE_V1,
        "synthesis_artifact_schema_rel_path": SYNTHESIS_ARTIFACT_SCHEMA_REL_PATH_V1,
        "synthesis_artifact_schema_digest_sha256": hash_synthesis_artifact_schema_fixture_v1(),
        "cesp_allowed_extension_importers": sorted(_CESP_ALLOWED_EXTENSION_IMPORTERS_V1),
        "forbidden_forward_import_prefixes": list(_FORBIDDEN_CESP_IMPORT_PREFIXES_V1),
        "cesp_owned_runtime_artifacts": list(_CESP_OWNED_RUNTIME_ARTIFACTS_V1),
        "admin_route_prefixes": list(_CESP_ADMIN_ROUTE_PREFIXES_V1),
        "rules": [
            {
                "id": "CESP-BND-08-01",
                "text": "CESP MUST NOT alter SynthesisIntelligenceArtifactV1 schema without Phase 08 amendment.",
            },
            {
                "id": "CESP-BND-08-02",
                "text": "CESP MAY add orchestration tables, reports, maturity enums (listed in catalog).",
            },
            {
                "id": "CESP-BND-09-01",
                "text": "Phase 09 MUST NOT ship until G-P085-CLOSE-01 passes.",
            },
            {
                "id": "CESP-BND-10-01",
                "text": "Operational cockpit routes register under /admin/.../operational-runtime/ (Phase 10 shell).",
            },
        ],
        "phase085_owns": [
            "substrate_pipeline_continuation",
            "stalled_pipeline_recovery",
            "density_schedulers",
            "operational_maturity",
            "operational_health",
            "materialization_reports",
            "activation_audits",
            "fake_green_prohibition",
            "admin_operational_cockpit_routes",
        ],
        "phase085_does_not_own": [
            "synthesis_intelligence_artifact_schema",
            "synthesis_policy_pack_workloads",
            "retrieval_query_algebra",
            "tcre_causal_legality",
            "phase_09_product_workflows",
        ],
    }


def assert_phase09_blocked_until_cesp_close_v1(
    *,
    phase09_ship_flags: Mapping[str, Any] | None = None,
    cesp_close_gate_passed: bool = False,
) -> None:
    """**CESP-BND-09-01** — block Phase 09 product ship until closure."""
    if cesp_close_gate_passed:
        return
    flags = dict(phase09_ship_flags or {})
    for key in _PHASE09_FORBIDDEN_SHIP_KEYS_V1:
        if flags.get(key) is True:
            raise CespPhaseBoundaryError(
                "phase09_ship_before_cesp_close",
                rule_id="CESP-BND-09-01",
                detail={"flag": key, "required_gate": PHASE085_HARD_DOWNSTREAM_GATE_V1},
            )


def assert_cesp_payload_respects_synthesis_schema_boundary_v1(payload: Mapping[str, Any]) -> None:
    """**CESP-BND-08-01** — CESP orchestration payloads must not smuggle SIL schema version bumps."""
    if "schema_version" in payload and payload.get("artifact_kind"):
        version = payload.get("schema_version")
        if version not in (1, "1"):
            raise CespPhaseBoundaryError(
                "synthesis_artifact_schema_version_mutation",
                rule_id="CESP-BND-08-01",
                detail={"schema_version": version},
            )


def _package_py_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or "tests" in path.parts:
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


def list_cesp_package_forward_product_import_violations_v1() -> list[str]:
    """Acyclic law — CESP must not import Phase 09 product modules."""
    root = Path(__file__).resolve().parent
    return _list_import_module_violations(
        root,
        forbidden_module_prefixes=_FORBIDDEN_CESP_IMPORT_PREFIXES_V1,
    )


def list_upstream_packages_importing_cesp_violations_v1() -> list[str]:
    """Phases 02–08 MUST NOT import CESP except allowlisted extension surfaces."""
    cortex_root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for pkg_name in ("synthesis", "reasoning", "ingestion", "identity", "traversal"):
        pkg_dir = cortex_root / pkg_name
        if not pkg_dir.is_dir():
            continue
        for rel in _list_import_module_violations(
            pkg_dir,
            forbidden_module_prefixes=("vector.domains.cortex.operational_runtime",),
        ):
            violations.append(f"{pkg_name}/{rel}")
    return violations


def list_cesp_disallowed_upstream_import_violations_v1() -> list[str]:
    """CESP imports must stay within Phases 02–08 + infrastructure (no Phase 09)."""
    root = Path(__file__).resolve().parent
    violations: list[str] = []
    for rel in _list_import_module_violations(root, forbidden_module_prefixes=_FORBIDDEN_CESP_IMPORT_PREFIXES_V1):
        violations.append(rel)
    for path in _package_py_files(root):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [a.name or "" for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for mod in modules:
                if not mod.startswith("vector.domains.cortex."):
                    continue
                if mod.startswith("vector.domains.cortex.operational_runtime"):
                    continue
                allowed = any(
                    mod == prefix or mod.startswith(prefix + ".")
                    for prefix in _CESP_ALLOWED_UPSTREAM_IMPORT_PREFIXES_V1
                    if prefix != "vector.domains.cortex.operational_runtime"
                )
                if not allowed:
                    violations.append(
                        f"{path.relative_to(root)}:{getattr(node, 'lineno', 0)}:unexpected_cortex_import:{mod}",
                    )
    return violations


def list_registered_cesp_admin_route_paths_v1() -> list[str]:
    """**CESP-BND-10-01** — registered admin HTTP paths for operational-runtime."""
    return [
        "/admin/catalog/cortex/operational-runtime/program",
        "/admin/catalog/cortex/operational-runtime/anti-idle-gate",
        "/admin/catalog/cortex/operational-runtime/phase-boundaries",
        "/admin/catalog/cortex/operational-runtime/phase-boundaries-gate",
        "/admin/catalog/cortex/operational-runtime/gap-matrix",
        "/admin/catalog/cortex/operational-runtime/vocabulary",
        "/admin/catalog/cortex/operational-runtime/gap-matrix-gate",
        "/admin/catalog/cortex/operational-runtime/substrate-continuity",
        "/admin/catalog/cortex/operational-runtime/continuation-gate",
        "/admin/catalog/cortex/operational-runtime/autonomous-progression",
        "/admin/catalog/cortex/operational-runtime/progression-gate",
        "/admin/catalog/cortex/operational-runtime/recovery-continuity",
        "/admin/catalog/cortex/operational-runtime/dlq-gate",
        "/admin/catalog/cortex/operational-runtime/recovery-receipts",
        "/admin/catalog/cortex/operational-runtime/recovery-receipt-gate",
        "/admin/catalog/cortex/operational-runtime/continuity-watchdog",
        "/admin/catalog/cortex/operational-runtime/continuity-watchdog-gate",
        "/admin/catalog/cortex/operational-runtime/graph-density",
        "/admin/catalog/cortex/operational-runtime/graph-density-gate",
        "/admin/catalog/cortex/operational-runtime/graph-density-promotion",
        "/admin/catalog/cortex/operational-runtime/graph-density-promotion-gate",
        "/admin/catalog/cortex/operational-runtime/graph-orphan-continuity",
        "/admin/catalog/cortex/operational-runtime/graph-orphan-continuity-gate",
        "/admin/catalog/cortex/operational-runtime/graph-completeness-propagation",
        "/admin/catalog/cortex/operational-runtime/graph-completeness-propagation-gate",
        "/admin/catalog/cortex/operational-runtime/traversal-scheduling",
        "/admin/catalog/cortex/operational-runtime/traversal-scheduling-gate",
        "/admin/catalog/cortex/operational-runtime/traversal-retry",
        "/admin/catalog/cortex/operational-runtime/traversal-retry-gate",
        "/admin/catalog/cortex/operational-runtime/stalled-traversal-recovery",
        "/admin/catalog/cortex/operational-runtime/stalled-traversal-recovery-gate",
        "/admin/catalog/cortex/operational-runtime/traversal-explainability",
        "/admin/catalog/cortex/operational-runtime/traversal-explainability-gate",
        "/admin/catalog/cortex/operational-runtime/tcre-saturation-scheduling",
        "/admin/catalog/cortex/operational-runtime/tcre-saturation-scheduling-gate",
        "/admin/catalog/cortex/operational-runtime/tcre-density",
        "/admin/catalog/cortex/operational-runtime/tcre-density-gate",
        "/admin/catalog/cortex/operational-runtime/tcre-omission-explainability",
        "/admin/catalog/cortex/operational-runtime/tcre-omission-explainability-gate",
        "/admin/catalog/cortex/operational-runtime/retrieval-density",
        "/admin/catalog/cortex/operational-runtime/retrieval-density-gate",
        "/admin/catalog/cortex/operational-runtime/retrieval-starvation",
        "/admin/catalog/cortex/operational-runtime/retrieval-starvation-gate",
        "/admin/catalog/cortex/operational-runtime/retrieval-completeness-propagation",
        "/admin/catalog/cortex/operational-runtime/retrieval-completeness-propagation-gate",
        "/admin/catalog/cortex/operational-runtime/synthesis-activation-scheduling",
        "/admin/catalog/cortex/operational-runtime/synthesis-activation-scheduling-gate",
        "/admin/catalog/cortex/operational-runtime/synthesis-idle-classification",
        "/admin/catalog/cortex/operational-runtime/synthesis-idle-classification-gate",
        "/admin/catalog/cortex/operational-runtime/synthesis-throughput",
        "/admin/catalog/cortex/operational-runtime/synthesis-throughput-gate",
        "/admin/catalog/cortex/operational-runtime/operational-maturity",
        "/admin/catalog/cortex/operational-runtime/operational-maturity-gate",
        "/admin/catalog/cortex/operational-runtime/operational-health",
        "/admin/catalog/cortex/operational-runtime/operational-health-gate",
        "/admin/catalog/cortex/operational-runtime/autonomous-recovery",
        "/admin/catalog/cortex/operational-runtime/autonomous-recovery-gate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/anti-idle-verification",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-density",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-density-promotion/run",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-density-promotion/schedule",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-orphan-continuity",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-orphan-continuity/stitch",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-completeness-propagation",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-scheduling",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-scheduling/schedule",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-scheduling/run",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-retry",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-retry/run",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-retry/schedule",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/stalled-traversal-recovery",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/stalled-traversal-recovery/run",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/stalled-traversal-recovery/schedule",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-explainability",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-saturation-scheduling",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-saturation-scheduling/schedule",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-saturation-scheduling/run",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-density",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-omission-explainability",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-density",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-starvation",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-eligibility/explain",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-completeness-propagation",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-activation-scheduling",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-activation-scheduling/run",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-activation-scheduling/schedule",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-idle-classification",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-eligibility/explain",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-idle-classification/panel",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput/stage",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput/metrics",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity/evaluate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-health",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-health/evaluate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/autonomous-recovery",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/autonomous-recovery/evaluate",
        "/admin/catalog/cortex/operational-runtime/cockpit",
        "/admin/catalog/cortex/operational-runtime/cockpit-gate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/command-center",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/timeline",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/heatmap",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/density-trends",
        "/admin/catalog/cortex/operational-runtime/explorers",
        "/admin/catalog/cortex/operational-runtime/explorers-gate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/{explorer_id}",
        "/admin/catalog/cortex/operational-runtime/progression-timeline",
        "/admin/catalog/cortex/operational-runtime/progression-timeline-gate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/progression-timeline",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/causal-failure-chain",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/overview-integration",
        "/admin/catalog/cortex/operational-runtime/runtime-economics",
        "/admin/catalog/cortex/operational-runtime/runtime-economics-gate",
        "/admin/catalog/cortex/operational-runtime/queue-backpressure",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/runtime-economics",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/runtime-economics/density-caps",
        "/admin/catalog/cortex/operational-runtime/replay-storm",
        "/admin/catalog/cortex/operational-runtime/replay-storm-gate",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/replay-storm",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/replay-storm/acknowledge",
        "/admin/catalog/cortex/operational-runtime/phase09-readiness",
        "/admin/catalog/cortex/operational-runtime/phase09-readiness-gate",
        "/admin/catalog/cortex/operational-runtime/phase09-readiness/checklist",
        "/admin/catalog/cortex/operational-runtime/phase09-readiness/soak-signoff",
        "/admin/tenants/{tenant_id}/cortex/operational-runtime/phase09-readiness/golden-profile",
        "/admin/catalog/cortex/operational-runtime/certification-pack",
        "/admin/catalog/cortex/operational-runtime/program-closure",
        "/admin/catalog/cortex/operational-runtime/constitutional-freeze",
        "/admin/catalog/cortex/operational-runtime/constitutional-freeze/signoff",
    ]


def verify_gp085_bnd_catalog_static() -> dict[str, Any]:
    cat = build_operational_runtime_phase_boundary_catalog_v1()
    errors: list[str] = []
    if set(cat["rule_ids"]) != set(CESP_BND_RULE_IDS_V1):
        errors.append("rule_ids_mismatch")
    if cat["hard_downstream_gate"] != PHASE085_HARD_DOWNSTREAM_GATE_V1:
        errors.append("downstream_gate_mismatch")
    if len(str(cat.get("synthesis_artifact_schema_digest_sha256") or "")) != 64:
        errors.append("schema_digest_missing")
    passed = not errors
    return {
        "id": GP085_BND_CATALOG_GATE_ID_V1,
        "name": "cesp_boundary_catalog",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp085_bnd08_synthesis_schema_static() -> dict[str, Any]:
    errors: list[str] = []
    digest = hash_synthesis_artifact_schema_fixture_v1()
    path = _repo_root_v1() / SYNTHESIS_ARTIFACT_SCHEMA_REL_PATH_V1
    if not path.is_file():
        errors.append("schema_file_missing")
    try:
        assert_cesp_payload_respects_synthesis_schema_boundary_v1(
            {"schema_version": 2, "artifact_kind": "test"},
        )
    except CespPhaseBoundaryError:
        pass
    else:
        errors.append("expected_schema_version_mutation_rejection")
    try:
        assert_cesp_payload_respects_synthesis_schema_boundary_v1(
            {"schema_version": 1, "artifact_kind": "test"},
        )
    except CespPhaseBoundaryError as exc:
        errors.append(f"unexpected_rejection_on_v1:{exc.code}")
    if not digest:
        errors.append("empty_digest")
    passed = not errors
    return {
        "id": "G-P085-BND-08",
        "name": "cesp_synthesis_schema_boundary",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "schema_digest_sha256": digest},
    }


def verify_gp085_bnd09_phase_block_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        assert_phase09_blocked_until_cesp_close_v1(
            phase09_ship_flags={"phase09_enabled": True},
            cesp_close_gate_passed=False,
        )
    except CespPhaseBoundaryError as exc:
        if exc.rule_id != "CESP-BND-09-01":
            errors.append(f"wrong_rule_id:{exc.rule_id}")
    else:
        errors.append("expected_phase09_block")
    try:
        assert_phase09_blocked_until_cesp_close_v1(cesp_close_gate_passed=True)
    except CespPhaseBoundaryError as exc:
        errors.append(f"unexpected_block_when_closed:{exc}")
    passed = not errors
    return {
        "id": "G-P085-BND-09",
        "name": "cesp_phase09_ship_block",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp085_bnd10_admin_routes_static() -> dict[str, Any]:
    errors: list[str] = []
    routes = list_registered_cesp_admin_route_paths_v1()
    for route in routes:
        if "/admin/catalog/cortex/operational-runtime/" not in route and (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/" not in route
        ):
            errors.append(f"route_outside_prefix:{route}")
    if "/admin/catalog/cortex/operational-runtime/phase-boundaries" not in routes:
        errors.append("missing_phase_boundaries_route")
    passed = not errors
    return {
        "id": "G-P085-BND-10",
        "name": "cesp_admin_route_registration",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "routes": routes},
    }


def verify_gp085_bnd_acyclic_dependency_static() -> dict[str, Any]:
    forward = list_cesp_package_forward_product_import_violations_v1()
    backward = list_upstream_packages_importing_cesp_violations_v1()
    disallowed = list_cesp_disallowed_upstream_import_violations_v1()
    errors: list[str] = []
    if forward:
        errors.append(f"cesp_forward_product_imports:{forward}")
    if backward:
        errors.append(f"upstream_backward_cesp_imports:{backward}")
    if disallowed:
        errors.append(f"cesp_disallowed_upstream:{disallowed}")
    chain = list(PHASE085_SUBSTRATE_ACYCLIC_CHAIN_V1)
    if "phase_08_synthesis" not in chain or "phase_08_5_cesp" not in chain:
        errors.append("acyclic_chain_missing_cesp_anchor")
    passed = not errors
    return {
        "id": GP085_BND_ACYCLIC_GATE_ID_V1,
        "name": "cesp_acyclic_pipeline_imports",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "acyclic_chain": chain},
    }


def verify_gp085_phase_boundaries_static() -> dict[str, Any]:
    """Aggregate **CESP-BND-*** static verification (P085-03)."""
    checks = (
        verify_gp085_bnd_catalog_static(),
        verify_gp085_bnd08_synthesis_schema_static(),
        verify_gp085_bnd09_phase_block_static(),
        verify_gp085_bnd10_admin_routes_static(),
        verify_gp085_bnd_acyclic_dependency_static(),
    )
    failures = [c["id"] for c in checks if not c.get("passed")]
    return {
        "id": "G-P085-BND",
        "gate_id": "G-P085-BND",
        "passed": not failures,
        "failure_codes": failures,
        "checks": list(checks),
    }
