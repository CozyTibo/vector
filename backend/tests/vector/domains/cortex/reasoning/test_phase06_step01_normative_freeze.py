"""P06-01 — Normative index + program freeze: doc contract + runtime metadata alignment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.normative import PHASE06_PROGRAM_FREEZE_VERSION


def _repo_root_containing_phase06_docs() -> Path:
    """Resolve repo root whether tests run from a full checkout or from ``/app`` in Docker."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "reasoning" / "phase-06-normative-index.md"
        if marker.is_file():
            return root
    pytest.fail(
        "Could not find DOCS/cortex/reasoning/phase-06-normative-index.md by walking parents "
        "from this test file. From Docker Compose, mount the repo DOCS tree read-only, e.g. "
        "``./DOCS:/app/DOCS:ro`` on the backend service used for ``make test``.",
    )


_REPO_ROOT = _repo_root_containing_phase06_docs()
_PHASE06_DIR = _REPO_ROOT / "DOCS" / "cortex" / "reasoning"

_REQUIRED_FILES = (
    "PHASE06_CONSTITUTIONAL_CHANGELOG.md",
    "PHASE06_IMPLEMENTATION_HANDOFF.md",
    "ambiguity-registry-v1.md",
    "bounded-ambiguity-law.md",
    "causal-breakpoint-detection-spec.md",
    "causal-degradation-spec.md",
    "causal-reconstruction-doctrine.md",
    "chronology-legality-law.md",
    "chronology-replay-legality-state-machine.md",
    "cross-system-causal-continuity.md",
    "deterministic-causal-chain-spec.md",
    "execution-causality-constraints.md",
    "execution-state-transition-law.md",
    "fixtures/ReasoningPolicyPackV1_Default.json",
    "organizational-continuity-reasoning.md",
    "phase-06-anti-goals-doctrine.md",
    "phase-06-normative-index.md",
    "reasoning-admin-control-plane-spec.md",
    "reasoning-idempotency-and-retry-doctrine.md",
    "reasoning-policy-pack-v1-default.md",
    "reasoning-policy-pack-v1.md",
    "reasoning-provenance-law.md",
    "reasoning-receipts-and-proof-artifacts.md",
    "reasoning-runtime-legality-matrix.md",
    "reasoning-spec-gap-matrix.md",
    "reasoning-verification-harness-spec.md",
    "replay-aware-reasoning-law.md",
    "replay-equivalence-reasoning-spec.md",
    "silence-causality-law.md",
    "temporal-anchor-resolution-spec.md",
    "temporal-conflict-resolution-law.md",
    "temporal-reasoning-doctrine.md",
    "tcre-causal-edge-registry-v1.md",
)

_VOCABULARY_TERMS = (
    "**TCRE**",
    "**TemporalAnchorChain**",
    "**ChronologyLegalityProjectionV1**",
    "**CHRON‑FORB‑1**",
    "**TCRECausalEdge_v1**",
    "**tcre_policy_bundle_digest**",
)


def test_phase06_program_freeze_version_matches_normative_index() -> None:
    text = (_PHASE06_DIR / "phase-06-normative-index.md").read_text(encoding="utf-8")
    m = re.search(
        r"\|\s*\*\*PHASE06_PROGRAM_FREEZE_VERSION\*\*\s*\|\s*`(\d+)`",
        text,
    )
    assert m is not None, (
        "normative index must declare PHASE06_PROGRAM_FREEZE_VERSION in Program freeze table"
    )
    assert int(m.group(1)) == PHASE06_PROGRAM_FREEZE_VERSION


@pytest.mark.parametrize("name", _REQUIRED_FILES)
def test_phase06_required_normative_files_exist(name: str) -> None:
    path = _PHASE06_DIR / name
    assert path.is_file(), f"missing {path.relative_to(_REPO_ROOT)}"


def test_phase06_normative_index_has_vocabulary_freeze_bundles_and_steps() -> None:
    text = (_PHASE06_DIR / "phase-06-normative-index.md").read_text(encoding="utf-8")
    assert "## Vocabulary" in text
    for bundle in (
        "**FF‑P06‑0**",
        "**FF‑P06‑1**",
        "**FF‑P06‑2**",
        "**FF‑P06‑3**",
        "**FF‑P06‑4**",
        "**FF‑P06‑5**",
    ):
        assert bundle in text, f"normative index must mention {bundle}"
    assert "| 1 | Normative index + program freeze" in text
    assert "| 35 | Closure + certification" in text
    for path in (
        "phase-06-anti-goals-doctrine.md",
        "reasoning-verification-harness-spec.md",
        "tcre-causal-edge-registry-v1.md",
        "reasoning-spec-gap-matrix.md",
    ):
        assert path in text, f"document hierarchy must reference {path}"


def test_phase06_normative_index_names_runtime_constant_path() -> None:
    text = (_PHASE06_DIR / "phase-06-normative-index.md").read_text(encoding="utf-8")
    assert "vector.domains.cortex.reasoning.normative.PHASE06_PROGRAM_FREEZE_VERSION" in text


def test_phase06_vocabulary_defines_core_terms() -> None:
    text = (_PHASE06_DIR / "phase-06-normative-index.md").read_text(encoding="utf-8")
    start = text.find("## Vocabulary")
    assert start != -1
    vocab_block = text[start : start + 8000]
    for term in _VOCABULARY_TERMS:
        assert term in vocab_block, f"vocabulary should define or mention {term!r}"
