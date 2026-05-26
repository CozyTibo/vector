"""Wave 6 — static grep gates for dead substrate/runtime residue (no runtime behavior)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

_CORTEX_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

# Production packages scanned for forbidden tokens (tests/archive excluded).
_WAVE6_SCAN_ROOTS_V1: Final[tuple[str, ...]] = (
    "execution",
    "substrate_pipeline",
    "identity",
    "ingestion",
    "operational_runtime",
    "pipeline",
    "convergence",
)

_WAVE6_EXCLUDED_DIR_NAMES_V1: Final[frozenset[str]] = frozenset(
    {
        "tests",
        "test",
        "__pycache__",
        "archive",
    }
)

# Substrings that must not appear in scanned production Python (module path hints).
_FORBIDDEN_SUBSTRINGS_V1: Final[tuple[str, ...]] = (
    "graph_hash_autonomous_chain",
    "continuity_p0_graph_hash_autonomous_chain",
    "cortex_graph_hash_autonomous_chain_enabled",
    "post_ingestion_refresh_celery_task_id",
    "run_graph_hash_autonomous_chain_v1",
    "seed_stale_graph_hash_for_chain_v1",
)

# Hot-path modules that must not import unlock wedge steps (autonomous execution only).
_WAVE6_UNLOCK_FREE_HOT_PATHS_V1: Final[tuple[str, ...]] = (
    "execution/run_tenant_execution.py",
    "execution/convergence_dispatch.py",
    "execution/execution_event_triggers.py",
    "substrate_pipeline/orchestrator.py",
    "identity/identity_substrate_repair_v1.py",
    "ingestion/post_ingestion_refresh_dispatch.py",
)

# Allowed importers of sync_executor shim (Wave 6: production uses sync_router).
_SYNC_EXECUTOR_SHIM_ALLOWED_V1: Final[frozenset[str]] = frozenset(
    {
        "ingestion/sync_executor.py",
        "ingestion/__init__.py",
    }
)

_SCHEDULE_SUBSTRATE_ALLOWED_V1: Final[frozenset[str]] = frozenset(
    {
        "substrate_pipeline/orchestrator.py",
        "substrate_pipeline/__init__.py",
        "operational_runtime/substrate_runtime_economics.py",
        "execution/scheduling.py",
    }
)


def _iter_scanned_py_files_v1() -> list[Path]:
    out: list[Path] = []
    for rel_root in _WAVE6_SCAN_ROOTS_V1:
        root = _CORTEX_ROOT / rel_root
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if any(part in _WAVE6_EXCLUDED_DIR_NAMES_V1 for part in path.parts):
                continue
            out.append(path)
    return out


def _rel_cortex_path(path: Path) -> str:
    try:
        return path.relative_to(_CORTEX_ROOT).as_posix()
    except ValueError:
        return path.name


def verify_forbidden_substrate_substrings_v1() -> list[str]:
    """Return error codes if dead experiment / fiction symbols remain in production tree."""
    errors: list[str] = []
    for path in _iter_scanned_py_files_v1():
        rel = _rel_cortex_path(path)
        if rel == "substrate_pipeline/substrate_residue_v1.py":
            continue
        if "/continuity_p0_" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_SUBSTRINGS_V1:
            if token in text:
                errors.append(f"forbidden_substring:{token}:{rel}")
    return errors


def verify_unlock_absent_from_autonomous_hot_paths_v1() -> list[str]:
    errors: list[str] = []
    for rel in _WAVE6_UNLOCK_FREE_HOT_PATHS_V1:
        path = _CORTEX_ROOT / rel
        if not path.is_file():
            errors.append(f"missing_hot_path:{rel}")
            continue
        if "vector.domains.cortex.unlock" in path.read_text(encoding="utf-8"):
            errors.append(f"unlock_import_in_hot_path:{rel}")
    return errors


def verify_sync_executor_not_in_production_imports_v1() -> list[str]:
    """Production cortex packages must import sync_router, not the sync_executor shim."""
    errors: list[str] = []
    pattern = re.compile(r"from\s+vector\.domains\.cortex\.ingestion\.sync_executor\s+import")
    for path in _iter_scanned_py_files_v1():
        rel = _rel_cortex_path(path)
        if rel in _SYNC_EXECUTOR_SHIM_ALLOWED_V1:
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            errors.append(f"sync_executor_import_in_production:{rel}")
    app_tasks = Path(__file__).resolve().parents[4] / "app" / "tasks" / "cortex_ingestion_sync.py"
    if app_tasks.is_file() and pattern.search(app_tasks.read_text(encoding="utf-8")):
        errors.append("sync_executor_import_in_production:app/tasks/cortex_ingestion_sync.py")
    return errors


def verify_schedule_substrate_pipeline_import_scope_v1() -> list[str]:
    """Compat wrapper may exist only in orchestrator + explicit allowlist (no new callers)."""
    errors: list[str] = []
    pattern = re.compile(r"schedule_substrate_pipeline_v1")
    for path in _iter_scanned_py_files_v1():
        rel = _rel_cortex_path(path)
        if rel == "substrate_pipeline/substrate_residue_v1.py":
            continue
        if rel in _SCHEDULE_SUBSTRATE_ALLOWED_V1:
            continue
        if "schedule_substrate_pipeline_v1" in path.read_text(encoding="utf-8"):
            errors.append(f"unexpected_schedule_substrate_pipeline_reference:{rel}")
    return errors


def verify_graph_density_schedule_scope_v1() -> list[str]:
    """schedule_graph_density_pass_v1 only in repair slice, promotion module, and debug/archive."""
    errors: list[str] = []
    allowed_prefixes = (
        "identity/identity_substrate_repair_v1.py",
        "operational_runtime/graph_density_promotion.py",
        "identity/debug_full_substrate_refresh_v1.py",
    )
    allowed_contains = (
        "execution/scheduling.py",
        "substrate_pipeline/continuity_p",
        "substrate_pipeline/substrate_residue_v1.py",
    )
    token = "schedule_graph_density_pass_v1"
    for path in _iter_scanned_py_files_v1():
        rel = _rel_cortex_path(path)
        text = path.read_text(encoding="utf-8")
        if token not in text:
            continue
        if rel in allowed_prefixes:
            continue
        if any(fragment in rel for fragment in allowed_contains):
            continue
        errors.append(f"graph_density_schedule_outside_repair:{rel}")
    return errors


def verify_no_substrate_residue_v1() -> list[str]:
    """Wave 6 exit gate — aggregate residue grep checks."""
    errors: list[str] = []
    errors.extend(verify_forbidden_substrate_substrings_v1())
    errors.extend(verify_unlock_absent_from_autonomous_hot_paths_v1())
    errors.extend(verify_sync_executor_not_in_production_imports_v1())
    errors.extend(verify_schedule_substrate_pipeline_import_scope_v1())
    errors.extend(verify_graph_density_schedule_scope_v1())
    return errors
