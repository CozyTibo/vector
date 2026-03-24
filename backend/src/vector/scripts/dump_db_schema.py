"""Emit a Ruby-on-Rails `schema.rb`-style snapshot of the live DB to stdout."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from vector.infrastructure.db.session import get_engine

_RAILS_DEFINE_LINE = "ActiveRecord::Schema[8.0].define(version: {version}) do"


def _alembic_version(engine: Engine) -> str | None:
    insp = inspect(engine)
    if "alembic_version" not in insp.get_table_names(schema="public"):
        return None
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).one_or_none()
    if row is None:
        return None
    return str(row[0])


def _rails_version_literal(version: str | None) -> str:
    if version is None:
        return "nil"
    if re.fullmatch(r"\d+", version):
        parts = [version[max(i - 3, 0) : i] for i in range(len(version), 0, -3)][::-1]
        joined = "_".join(parts)
        return joined
    return repr(version)


def _rails_type_and_options(sa_type: Any) -> tuple[str, list[str]]:
    """Map a reflected SQLAlchemy type to (rails_method, extra_option_strings)."""
    opts: list[str] = []
    s = str(sa_type).strip()

    if re.match(r"^UUID", s, re.I):
        return "uuid", opts

    m = re.match(r"^VARCHAR\((\d+)\)", s, re.I)
    if m:
        opts.append(f"limit: {m.group(1)}")
        return "string", opts

    m = re.match(r"^CHAR\((\d+)\)", s, re.I)
    if m:
        opts.append(f"limit: {m.group(1)}")
        return "string", opts

    if re.match(r"^TEXT", s, re.I):
        return "text", opts

    if re.match(r"^BOOLEAN", s, re.I):
        return "boolean", opts

    if re.match(r"^SMALLINT", s, re.I):
        return "integer", opts

    if re.match(r"^INTEGER", s, re.I):
        return "integer", opts

    if re.match(r"^BIGINT", s, re.I):
        return "bigint", opts

    m = re.match(r"^NUMERIC\((\d+)\s*,\s*(\d+)\)", s, re.I)
    if m:
        opts.extend([f"precision: {m.group(1)}", f"scale: {m.group(2)}"])
        return "decimal", opts

    if re.match(r"^DOUBLE PRECISION", s, re.I):
        return "float", opts

    if re.match(r"^REAL", s, re.I):
        return "float", opts

    if re.match(r"^DATE\b", s, re.I):
        return "date", opts

    if re.match(r"^TIME\b", s, re.I):
        return "time", opts

    if "JSONB" in s.upper():
        return "jsonb", opts

    if "JSON" in s.upper():
        return "json", opts

    m = re.match(r"^BYTEA", s, re.I)
    if m:
        return "binary", opts

    if "TIMESTAMP" in s.upper() or "DATETIME" in s.upper():
        opts.append("precision: 6")
        return "datetime", opts

    # Fallback: show raw SQL type in a comment-friendly way
    return "string", [repr(s)]


def _format_default(default: Any) -> str | None:
    if default is None:
        return None
    d = str(default).strip()
    if not d or d.upper() == "NULL":
        return None
    if len(d) > 80:
        d = d[:77] + "..."
    return repr(d)


def _emit_create_table(engine: Engine, table: str, lines: list[str]) -> None:
    insp = inspect(engine)
    pk = insp.get_pk_constraint(table)
    pks = set(pk.get("constrained_columns") or ())

    lines.append(f'  create_table "{table}", force: :cascade do |t|')

    for col in insp.get_columns(table):
        name = col["name"]
        rails_t, extra_opts = _rails_type_and_options(col["type"])
        parts: list[str] = [f'"{name}"']

        for opt in extra_opts:
            if opt.startswith("limit:") or opt.startswith("precision:") or opt.startswith("scale:"):
                parts.append(opt)
            elif opt.startswith('"') or opt.startswith("'"):
                # Fallback raw type stored as string literal — attach as comment only
                continue

        if name in pks:
            parts.append("null: false")
        elif not col.get("nullable", True):
            parts.append("null: false")

        default_ruby = _format_default(col.get("default"))
        if default_ruby is not None:
            parts.append(f"default: {default_ruby}")

        line = f"    t.{rails_t} {', '.join(parts)}"

        if extra_opts and (extra_opts[0].startswith('"') or extra_opts[0].startswith("'")):
            line += f"  # SQL type: {extra_opts[0]}"

        lines.append(line)

    for idx in insp.get_indexes(table):
        col_names = [c for c in idx["column_names"] if c is not None]
        if not col_names:
            iname = idx.get("name") or "?"
            lines.append(f"    # t.index omitted (non-column index: {iname})")
            continue
        if idx.get("unique"):
            cols = ", ".join(f'"{c}"' for c in col_names)
            opts = f', name: "{idx["name"]}"' if idx.get("name") else ""
            lines.append(f"    t.index [{cols}], unique: true{opts}")
        else:
            cols = ", ".join(f'"{c}"' for c in col_names)
            opts = f', name: "{idx["name"]}"' if idx.get("name") else ""
            lines.append(f"    t.index [{cols}]{opts}")

    lines.append("  end")
    lines.append("")


def _emit_foreign_keys(engine: Engine, table: str, lines: list[str]) -> None:
    insp = inspect(engine)
    for fk in insp.get_foreign_keys(table):
        ref = fk["referred_table"]
        cols = fk["constrained_columns"]
        ref_cols = fk["referred_columns"]
        if len(cols) != 1 or len(ref_cols) != 1:
            continue
        col, ref_col = cols[0], ref_cols[0]
        opts: list[str] = [f'column: "{col}"']
        if ref_col != "id":
            opts.append(f'primary_key: "{ref_col}"')
        ondelete = (fk.get("options") or {}).get("ondelete")
        if ondelete is not None:
            od = str(ondelete).upper()
            if od == "CASCADE":
                opts.append("on_delete: :cascade")
            elif od == "SET NULL":
                opts.append("on_delete: :nullify")
            elif od == "RESTRICT":
                opts.append("on_delete: :restrict")

        opt_str = ", ".join(opts)
        lines.append(f'  add_foreign_key "{table}", "{ref}", {opt_str}')


def main() -> None:
    engine = get_engine()
    generated = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S %Z")

    lines: list[str] = [
        "# This file is auto-generated by `make db-schema`.",
        "# Live PostgreSQL schema, Rails schema.rb-style layout (reference only).",
        f"# Generated at: {generated}",
        "",
    ]

    version = _alembic_version(engine)
    lines.append(_RAILS_DEFINE_LINE.format(version=_rails_version_literal(version)))
    lines.append("")

    insp = inspect(engine)
    tables = sorted(insp.get_table_names(schema="public"))

    for table in tables:
        _emit_create_table(engine, table, lines)

    fk_lines: list[str] = []
    for table in tables:
        _emit_foreign_keys(engine, table, fk_lines)

    if fk_lines:
        lines.extend(fk_lines)
        lines.append("")

    lines.append("end")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
