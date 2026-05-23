"""Phase C3 — deprecation notices for per-phase continuity proof scripts."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Final

CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1: Final[str] = "continuity_audit_snapshot.py"
CANONICAL_AUDIT_SNAPSHOT_MODULE_V1: Final[str] = (
    "vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot"
)

_DEPRECATION_EXEMPT_SCRIPT_NAMES_V1: Final[frozenset[str]] = frozenset(
    {
        CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1,
    }
)


def deprecated_continuity_proof_script_names_v1(*, scripts_dir: Path | None = None) -> tuple[str, ...]:
    """All ``continuity_*_proof.py`` CLI scripts except the canonical audit snapshot."""
    root = scripts_dir or Path(__file__).resolve().parents[6] / "backend" / "scripts"
    names: list[str] = []
    if root.is_dir():
        for path in sorted(root.glob("continuity_*_proof.py")):
            if path.name not in _DEPRECATION_EXEMPT_SCRIPT_NAMES_V1:
                names.append(path.name)
    for extra in (
        "continuity_proof_panel.py",
        "prod_substrate_proof_queries.py",
    ):
        if extra not in names:
            names.append(extra)
    return tuple(names)


DEPRECATED_CONTINUITY_PROOF_SCRIPTS_V1: Final[tuple[str, ...]] = deprecated_continuity_proof_script_names_v1()


def deprecation_message_for_script_v1(script_path: str | Path) -> str:
    name = Path(script_path).name
    return (
        f"{name} is deprecated (Phase C3). Use backend/scripts/"
        f"{CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1} for unified JSON + AA panel + SQL snapshot. "
        "Per-phase proof scripts remain for CI step gates only."
    )


def warn_deprecated_continuity_proof_script_v1(script_path: str | Path) -> None:
    """Emit ``DeprecationWarning`` when a legacy proof script is executed."""
    warnings.warn(
        deprecation_message_for_script_v1(script_path),
        DeprecationWarning,
        stacklevel=3,
    )
