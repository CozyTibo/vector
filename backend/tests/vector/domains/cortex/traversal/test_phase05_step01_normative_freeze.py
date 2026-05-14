"""P05-01 — Normative index + program freeze: doc contract + runtime metadata alignment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vector.domains.cortex.traversal.normative import PHASE05_PROGRAM_FREEZE_VERSION


def _repo_root_containing_phase05_docs() -> Path:
    """Resolve repo root whether tests run from a full checkout or from ``/app`` in Docker."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    pytest.fail(
        "Could not find DOCS/cortex/05-traversal/phase-05-normative-index.md by walking parents "
        "from this test file. From Docker Compose, mount the repo DOCS tree read-only, e.g. "
        "``./DOCS:/app/DOCS:ro`` on the backend service used for ``make test``.",
    )


_REPO_ROOT = _repo_root_containing_phase05_docs()
_PHASE05_DIR = _REPO_ROOT / "DOCS" / "cortex" / "05-traversal"

_REQUIRED_FILES = (
    "phase-05-normative-index.md",
    "phase-05-observed-vs-derived-doctrine.md",
    "phase-05-anti-goals-doctrine.md",
    "phase-05-graph-import-boundary-doctrine.md",
    "phase-05-traversal-vs-reasoning-doctrine.md",
    "phase-05-multigraph-model-doctrine.md",
    "phase-05-temporal-walk-doctrine.md",
    "phase-05-walk-policy-doctrine.md",
    "phase-05-walk-result-contract.md",
    "phase-05-hop-receipt-doctrine.md",
    "phase-05-exploration-mode-doctrine.md",
    "phase-05-walk-diagnostics-doctrine.md",
    "phase-05-derived-index-contract-doctrine.md",
    "phase-05-index-build-job-doctrine.md",
    "phase-05-walk-execution-strategy-doctrine.md",
    "phase-05-runtime-execution-model.md",
    "phase-05-walk-api-contracts.md",
    "phase-05-idempotency-and-retry-doctrine.md",
    "phase-05-walk-replay-doctrine.md",
    "phase-05-index-replay-doctrine.md",
    "phase-05-traversal-equivalence-doctrine.md",
    "phase-05-verification-gates-doctrine.md",
    "phase-05-tenant-verification-integration.md",
    "phase-05-control-plane-doctrine.md",
    "phase-05-readiness-economics-doctrine.md",
    "phase-05-closure-gates-doctrine.md",
    "phase-05-canonicalization-profile.md",
    "phase-05-ci-enforcement-architecture.md",
    "phase-05-runtime-legality-matrix.md",
    "phase-05-certification-pack-format.md",
    "phase-05-spec-gap-matrix.md",
    "phase-05-replay-integrity-matrix.md",
    "phase-05-corruption-vectors.md",
)

_VOCABULARY_TERMS = (
    "**Walk**",
    "**Observed hop**",
    "**Derived hop**",
    "**Temporal anchor**",
    "**edge_fingerprint**",
)


def test_phase05_program_freeze_version_matches_normative_index() -> None:
    text = (_PHASE05_DIR / "phase-05-normative-index.md").read_text(encoding="utf-8")
    m = re.search(
        r"\|\s*\*\*PHASE05_PROGRAM_FREEZE_VERSION\*\*\s*\|\s*`(\d+)`",
        text,
    )
    assert m is not None, (
        "normative index must declare PHASE05_PROGRAM_FREEZE_VERSION in Program freeze table"
    )
    assert int(m.group(1)) == PHASE05_PROGRAM_FREEZE_VERSION


@pytest.mark.parametrize("name", _REQUIRED_FILES)
def test_phase05_required_normative_files_exist(name: str) -> None:
    path = _PHASE05_DIR / name
    assert path.is_file(), f"missing {path.relative_to(_REPO_ROOT)}"


def test_phase05_schemas_and_waivers_sidecars_exist() -> None:
    schemas = _PHASE05_DIR / "schemas"
    assert schemas.is_dir(), "schemas/ must exist under 05-traversal"
    assert any(schemas.glob("*.schema.json")), "schemas/ must contain at least one *.schema.json"
    waivers = _PHASE05_DIR / "waivers" / "verification_waivers.yaml"
    assert waivers.is_file(), f"missing {waivers.relative_to(_REPO_ROOT)}"


def test_phase05_golden_vectors_readme_exists() -> None:
    readme = Path(__file__).resolve().parent / "octs_golden_vectors" / "v1" / "README.md"
    assert readme.is_file(), f"missing canonical vector root {readme}"


def test_phase05_normative_index_has_vocabulary_freeze_bundles_and_steps() -> None:
    text = (_PHASE05_DIR / "phase-05-normative-index.md").read_text(encoding="utf-8")
    assert "## Vocabulary" in text
    for bundle in ("**FF-0**", "**FF-1**", "**FF-2**", "**FF-3**", "**FF-4**", "**FF-5**"):
        assert bundle in text, f"normative index must mention {bundle}"
    assert "| 1 | Normative index + program freeze" in text
    assert "| 26 | Closure gates" in text
    for path in (
        "phase-05-canonicalization-profile.md",
        "phase-05-ci-enforcement-architecture.md",
        "phase-05-certification-pack-format.md",
    ):
        assert path in text, f"document hierarchy must reference {path}"


def test_phase05_normative_index_names_runtime_constant_path() -> None:
    text = (_PHASE05_DIR / "phase-05-normative-index.md").read_text(encoding="utf-8")
    assert "vector.domains.cortex.traversal.normative.PHASE05_PROGRAM_FREEZE_VERSION" in text


def test_phase05_vocabulary_defines_core_terms() -> None:
    text = (_PHASE05_DIR / "phase-05-normative-index.md").read_text(encoding="utf-8")
    start = text.find("## Vocabulary")
    assert start != -1
    vocab_block = text[start : start + 8000]
    for term in _VOCABULARY_TERMS:
        assert term in vocab_block, f"vocabulary should define or mention {term!r}"
