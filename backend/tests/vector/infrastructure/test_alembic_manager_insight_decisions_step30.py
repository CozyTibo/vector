"""§6 Steps 30 + 39 — Alembic head includes decisions (0026) then outcomes/policy (0027)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_head_is_step30_manager_insight_decisions() -> None:
    backend_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_root / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["20260430_0027"]
    rev27 = script.get_revision("20260430_0027")
    assert rev27.down_revision == "20260430_0026"
    rev26 = script.get_revision("20260430_0026")
    assert rev26.down_revision == "20260430_0025"
