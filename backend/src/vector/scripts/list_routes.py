"""Print HTTP routes in a grouped, Rails-style layout."""

from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Route

_METHOD_ORDER = {"GET": 0, "POST": 1, "PUT": 2, "PATCH": 3, "DELETE": 4}
_TAG_ORDER = {"health": 0, "auth": 1, "me": 2}


class _Row(NamedTuple):
    method: str
    path: str
    name: str


def _method_key(method: str) -> int:
    return _METHOD_ORDER.get(method, 99)


def _tag_sort_key(tag: str) -> tuple[int, str]:
    return (_TAG_ORDER.get(tag, 50), tag)


def _primary_tag(route: APIRoute) -> str:
    if route.tags:
        return str(route.tags[0])
    parts = [p for p in route.path.strip("/").split("/") if p]
    return parts[0] if parts else "(root)"


def _collect_api_routes(app: FastAPI) -> dict[str, list[_Row]]:
    by_tag: dict[str, list[_Row]] = defaultdict(list)
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        tag = _primary_tag(route)
        for method in sorted(route.methods, key=_method_key):
            m = str(method)
            if m in ("HEAD", "OPTIONS"):
                continue
            by_tag[tag].append(_Row(m, route.path, route.name))
    for tag in by_tag:
        by_tag[tag].sort(key=lambda r: (r.path, _method_key(r.method)))
    return by_tag


def _collect_framework_routes(app: FastAPI) -> list[_Row]:
    rows: list[_Row] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            continue
        if not isinstance(route, Route):
            continue
        raw = route.methods
        methods: set[str] = {str(m) for m in raw} if raw else set()
        for method in sorted(methods, key=_method_key):
            if method in ("HEAD", "OPTIONS"):
                continue
            rows.append(_Row(method, route.path, route.name or ""))
    rows.sort(key=lambda r: (r.path, _method_key(r.method)))
    return rows


def _widths(rows: list[_Row]) -> tuple[int, int]:
    if not rows:
        return 6, 24
    w_m = max(len(r.method) for r in rows)
    w_p = max(len(r.path) for r in rows)
    return max(w_m, 6), max(w_p, 12)


def _print_rows(rows: list[_Row], w_method: int, w_path: int) -> None:
    hdr_m = "METHOD"
    hdr_p = "PATH"
    hdr_e = "ENDPOINT"
    print(f"  {hdr_m:<{w_method}}  {hdr_p:<{w_path}}  {hdr_e}")
    print(f"  {'-' * w_method}  {'-' * w_path}  {'-' * max(18, len(hdr_e))}")
    for row in rows:
        print(f"  {row.method:<{w_method}}  {row.path:<{w_path}}  {row.name}")


def main() -> None:
    from vector.api.http.main import app

    by_tag = _collect_api_routes(app)
    framework = _collect_framework_routes(app)

    app_rows = [r for tag in sorted(by_tag.keys(), key=_tag_sort_key) for r in by_tag[tag]]
    all_rows = app_rows + framework
    w_method, w_path = _widths(all_rows)

    print("Vector HTTP routes (grouped by OpenAPI tag)")
    print("=" * (w_method + w_path + 32))
    print()

    for tag in sorted(by_tag.keys(), key=_tag_sort_key):
        section = by_tag[tag]
        print(f"[{tag}]")
        _print_rows(section, w_method, w_path)
        print()

    if framework:
        print("[openapi & docs]")
        _print_rows(framework, w_method, w_path)


if __name__ == "__main__":
    main()
