"""Reset alembic_version when it references a revision missing from the local script tree (branch switch)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import create_engine, inspect, text


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("repair_alembic_version: DATABASE_URL is required", file=sys.stderr)
        return 1

    root = Path(__file__).resolve().parents[3]
    ini = root / "alembic.ini"
    if not ini.is_file():
        print(f"repair_alembic_version: missing {ini}", file=sys.stderr)
        return 1

    cfg = Config(str(ini))
    script = ScriptDirectory.from_config(cfg)
    engine = create_engine(url)

    insp = inspect(engine)
    if not insp.has_table("alembic_version"):
        print("repair_alembic_version: no alembic_version table yet; nothing to do")
        return 0

    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()

    if row is None or not row[0]:
        print("repair_alembic_version: alembic_version is empty; nothing to do")
        return 0

    current = str(row[0]).strip()
    try:
        script.get_revision(current)
    except CommandError:
        print(f"repair_alembic_version: unknown revision {current!r}; stamping head")
        command.stamp(cfg, "head")
        return 0

    print(f"repair_alembic_version: revision {current!r} is valid; nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
