"""Phase 05 Step **23** — ``org_graph_traversal`` tenant verification aggregate slice.

Normative: ``DOCS/cortex/05-traversal/phase-05-tenant-verification-integration.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Final, Mapping, cast

import jsonschema  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from vector.domains.cortex.traversal.normative import PHASE05_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.traversal.walk_api_contract import octs_walk_api_memory_store_v1


def _repo_root_with_octs_docs() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        if (root / "DOCS" / "cortex" / "05-traversal").is_dir():
            return root
    msg = "could not locate DOCS/cortex/05-traversal from tenant_verification_slice"
    raise RuntimeError(msg)


def _octs_tests_tree_root_v1(repo: Path) -> Path:
    if (repo / "tests").is_dir():
        return repo / "tests"
    if (repo / "backend" / "tests").is_dir():
        return repo / "backend" / "tests"
    msg = f"could not locate tests tree under {repo}"
    raise RuntimeError(msg)


def octs_golden_vectors_v1_root_for_tenant_slice() -> Path:
    """Golden vectors root (duplicated from ``verification_gates_catalog`` to avoid import cycles)."""
    repo = _repo_root_with_octs_docs()
    return (
        _octs_tests_tree_root_v1(repo)
        / "vector"
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
    )

ORG_GRAPH_TRAVERSAL_VERIFICATION_SLICE_SCHEMA_VERSION: Final[int] = 1

VECTOR_OCTS_TENANT_VERIFICATION_SLICE_ENV: Final[str] = "VECTOR_OCTS_TENANT_VERIFICATION_SLICE"

# Sentinel: no attached PR gate bundle file on the run (structural-only slice).
_LAST_GATE_BUNDLE_EMPTY_CANONICAL_SHA256: Final[str] = hashlib.sha256(
    json.dumps({}, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def octs_org_graph_traversal_verification_slice_schema_path() -> Path:
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        p = root / "DOCS" / "cortex" / "05-traversal" / "schemas" / "octs-org-graph-traversal-verification-slice-v1.schema.json"
        if p.is_file():
            return p
    msg = "could not locate octs-org-graph-traversal-verification-slice-v1.schema.json"
    raise RuntimeError(msg)


def octs_tenant_verification_slice_enabled_v1() -> bool:
    return os.environ.get(VECTOR_OCTS_TENANT_VERIFICATION_SLICE_ENV, "").lower() in (
        "1",
        "true",
        "yes",
    )


def _any_float(obj: Any) -> bool:
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_any_float(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_any_float(v) for v in obj)
    return False


def list_fs_tv01_slice_float_violations_v1(slice_body: Mapping[str, Any]) -> list[str]:
    """**FS-TV-01** companion — slice JSON must not carry floats (counts are integers only)."""
    if _any_float(slice_body):
        return ["float_in_org_graph_traversal_slice"]
    return []


def validate_org_graph_traversal_verification_slice_v1(
    doc: Mapping[str, Any],
) -> list[str]:
    """Structural + JSON Schema validation for **G-P05-TVER-01**."""
    errs = list_fs_tv01_slice_float_violations_v1(doc)
    try:
        schema = json.loads(octs_org_graph_traversal_verification_slice_schema_path().read_text(encoding="utf-8"))
        jsonschema.validate(instance=dict(doc), schema=schema)
    except jsonschema.ValidationError as exc:
        errs.append(f"jsonschema:{exc.message}")
    except jsonschema.SchemaError as exc:
        errs.append(f"jsonschema_schema_error:{exc.message}")
    return errs


def compute_octs_slice_hash_v1(slice_body: Mapping[str, Any]) -> str:
    """Deterministic sha256 over sorted compact JSON (certification body per Step 23 §5)."""
    payload = json.dumps(dict(slice_body), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_org_graph_traversal_verification_slice_v1(
    _session: Session,
    *,
    tenant_id: Any,
    verification_run_id: str | None,
) -> dict[str, Any]:
    """Bounded ``org_graph_traversal`` aggregate for tenant verification evidence (integers only).

    ``_session`` is reserved for future durable index / job queries (**index_epoch**, queue depth).
    """
    tid = str(tenant_id)
    depth = octs_walk_api_memory_store_v1().walk_queue_depth_for_tenant(tenant_id)
    body: dict[str, Any] = {
        "index_lag_epochs": 0,
        "last_gate_bundle_sha256": _LAST_GATE_BUNDLE_EMPTY_CANONICAL_SHA256,
        "last_index_epoch": 0,
        "octs_program_freeze_version": int(PHASE05_PROGRAM_FREEZE_VERSION),
        "org_graph_traversal_slice_schema_version": ORG_GRAPH_TRAVERSAL_VERIFICATION_SLICE_SCHEMA_VERSION,
        "tenant_id": tid,
        "verification_run_id": verification_run_id,
        "walk_queue_depth": int(depth),
    }
    # Deterministic key order for human diffs (hash uses sort_keys anyway).
    return dict(sorted(body.items()))


def verify_gp05_tver01_org_graph_traversal_slice_golden_static() -> dict[str, Any]:
    """**G-P05-TVER-01** — golden tenant ``org_graph_traversal`` slice matches schema + hash law."""
    errors: list[str] = []
    path = octs_golden_vectors_v1_root_for_tenant_slice() / "tenant_verification" / "org_graph_traversal_slice_good_v1.json"
    if not path.is_file():
        errors.append(f"missing_golden:{path}")
        return _tver_gate(errors)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            errors.append("golden_not_object")
            return _tver_gate(errors)
        errors.extend(validate_org_graph_traversal_verification_slice_v1(cast(Mapping[str, Any], doc)))
        if doc.get("octs_program_freeze_version") != PHASE05_PROGRAM_FREEZE_VERSION:
            errors.append("golden_freeze_version_mismatch_normative")
        h1 = compute_octs_slice_hash_v1(cast(Mapping[str, Any], doc))
        h2 = compute_octs_slice_hash_v1(cast(Mapping[str, Any], doc))
        if h1 != h2:
            errors.append("slice_hash_non_deterministic")
    except json.JSONDecodeError as exc:
        errors.append(f"json_invalid:{exc}")
    return _tver_gate(errors)


def _tver_gate(errors: list[str]) -> dict[str, Any]:
    from vector.domains.cortex.traversal.verification_gates_catalog import default_severity_for_gate_v1

    return {
        "id": "G-P05-TVER-01",
        "name": "org_graph_traversal_tenant_verification_slice",
        "passed": len(errors) == 0,
        "severity": default_severity_for_gate_v1("G-P05-TVER-01"),
        "detail": {"errors": errors},
    }
