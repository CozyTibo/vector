"""Overview module must import cleanly (regression: missing sqlalchemy.select)."""

import ast
from pathlib import Path


def test_overview_imports_select() -> None:
    path = (
        Path(__file__).resolve().parents[5]
        / "src"
        / "vector"
        / "domains"
        / "cortex"
        / "execution_surfaces"
        / "overview.py"
    )
    tree = ast.parse(path.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "sqlalchemy":
            for alias in node.names:
                imported.add(alias.name)
    assert "select" in imported
