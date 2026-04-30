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

# DBs stamped with a typo / orphan id that matches no file.
# Map to the *parent* of the intended migration so `alembic upgrade head` still runs the real
# revision’s DDL. Mapping directly to the head id would skip the migration (empty table).
# (20260427_0024 is now the real Notion/Calls revision — do not alias it.)
_REVISION_ALIASES: dict[str, str] = {}


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

    # Stamped at 0024 without running the migration (e.g. earlier repair mapped typo -> head id).
    # Rewind to parent so a following `alembic upgrade head` applies the real DDL.
    if current == "20260429_0024" and not insp.has_table("password_reset_tokens"):
        parent = "20260422_0023"
        print(
            f"repair_alembic_version: {current!r} but password_reset_tokens missing; "
            f"rewriting to {parent!r} so upgrade can apply"
        )
        with engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": parent})
        return 0

    if current in _REVISION_ALIASES:
        target = _REVISION_ALIASES[current]
        try:
            script.get_revision(target)
        except CommandError:
            print(
                f"repair_alembic_version: alias target {target!r} missing from scripts; "
                "falling back to clear + stamp",
                file=sys.stderr,
            )
        else:
            print(f"repair_alembic_version: rewriting {current!r} -> {target!r}")
            with engine.begin() as conn:
                conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": target})
            return 0

    try:
        script.get_revision(current)
    except CommandError:
        # stamp("head") still resolves the broken row and fails; clear first, then stamp.
        print(f"repair_alembic_version: unknown revision {current!r}; clearing alembic_version and stamping head")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM alembic_version"))
        command.stamp(cfg, "head")
        return 0

    print(f"repair_alembic_version: revision {current!r} is valid; nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
