"""Alembic head verification for current schema baseline."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_head_is_step30_manager_insight_decisions() -> None:
    backend_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["20260507_0028"]
    rev28 = script.get_revision("20260507_0028")
    assert rev28.down_revision == "20260430_0027"
    rev27 = script.get_revision("20260430_0027")
    assert rev27.down_revision == "20260430_0026"
    rev26 = script.get_revision("20260430_0026")
    assert rev26.down_revision == "20260430_0025"
