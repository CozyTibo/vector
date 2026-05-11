"""P04-01 — Normative index + program freeze: doc contract + metadata alignment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vector.domains.cortex.identity.normative import PHASE04_PROGRAM_FREEZE_VERSION


def _repo_root_containing_phase04_docs() -> Path:
    """Resolve repo root whether tests run from a full checkout or from ``/app`` in Docker.

    ``parents[N]`` is brittle: in the backend image, ``/app/tests/...`` has only five parents
    before ``/``, so a fixed depth wrongly yields ``/DOCS/...``.
    """
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "04-identity" / "phase-04-normative-index.md"
        if marker.is_file():
            return root
    pytest.fail(
        "Could not find DOCS/cortex/04-identity/phase-04-normative-index.md by walking parents "
        "from this test file. From Docker Compose, mount the repo DOCS tree read-only, e.g. "
        "``./DOCS:/app/DOCS:ro`` on the backend service used for ``make test``.",
    )


_REPO_ROOT = _repo_root_containing_phase04_docs()
_PHASE04_DIR = _REPO_ROOT / "DOCS" / "cortex" / "04-identity"

_REQUIRED_FILES = (
    "phase-04-normative-index.md",
    "phase-04-anti-goals-doctrine.md",
    "phase-04-architecture-identity-linking-doctrine.md",
    "phase-04-implementation-plan.md",
    "phase-04-control-plane-doctrine.md",
    "phase-04-mock-data-strategy.md",
    "phase-04-topology-vs-meaning-doctrine.md",
)

_GLOSSARY_TERMS = (
    "Org handle",
    "Topology",
    "Meaning link",
    "Candidate link",
    "Authoritative link",
    "Hint",
    "Merge record",
    "Execution primitive instance",
    "Execution Continuity Operator Console",
)


def test_phase04_program_freeze_version_matches_normative_index() -> None:
    text = (_PHASE04_DIR / "phase-04-normative-index.md").read_text(encoding="utf-8")
    m = re.search(
        r"\|\s*\*\*PHASE04_PROGRAM_FREEZE_VERSION\*\*\s*\|\s*`(\d+)`",
        text,
    )
    assert m is not None, (
        "normative index must declare PHASE04_PROGRAM_FREEZE_VERSION in Program freeze table"
    )
    assert int(m.group(1)) == PHASE04_PROGRAM_FREEZE_VERSION


@pytest.mark.parametrize("name", _REQUIRED_FILES)
def test_phase04_required_normative_files_exist(name: str) -> None:
    path = _PHASE04_DIR / name
    assert path.is_file(), f"missing {path.relative_to(_REPO_ROOT)}"


def test_phase04_normative_index_has_glossary_and_stage_table() -> None:
    text = (_PHASE04_DIR / "phase-04-normative-index.md").read_text(encoding="utf-8")
    assert "## Vocabulary" in text or "## Vocabulary (non-negotiable" in text
    assert "P04-01" in text and "P04-22" in text
    for term in _GLOSSARY_TERMS:
        assert term in text, f"glossary should mention {term!r}"


def test_phase04_normative_index_lists_anti_goals_as_shipped() -> None:
    text = (_PHASE04_DIR / "phase-04-normative-index.md").read_text(encoding="utf-8")
    assert "phase-04-anti-goals-doctrine.md" in text
    assert "**Shipped**" in text
    # Inventory row for anti-goals must be Shipped (not Planned-only)
    assert re.search(
        r"`phase-04-anti-goals-doctrine\.md`\s*\|\s*\*\*Shipped\*\*",
        text,
    ), "anti-goals doctrine must be marked Shipped in inventory"


def test_phase04_anti_goals_covers_core_boundaries() -> None:
    text = (_PHASE04_DIR / "phase-04-anti-goals-doctrine.md").read_text(encoding="utf-8")
    for phrase in (
        "Phase 05",
        "embedding",
        "hint",
        "topology",
        "retroactive",
    ):
        assert phrase.lower() in text.lower()
