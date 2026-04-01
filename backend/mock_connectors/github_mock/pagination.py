"""GitHub-style `Link` pagination headers (local mock)."""

from __future__ import annotations

from urllib.parse import urlencode

from starlette.requests import Request


def github_link_header(
    request: Request,
    *,
    page: int,
    per_page: int,
    total_items: int,
) -> dict[str, str]:
    """Mirror common GitHub REST `Link` header (next, prev, first, last)."""
    if total_items <= 0:
        return {}

    total_pages = max(1, (total_items + per_page - 1) // per_page)
    base = str(request.base_url).rstrip("/")
    path = request.url.path
    # Normalize path (Starlette may include app root)
    if not path.startswith("/"):
        path = "/" + path

    def link_url(p: int) -> str:
        q = urlencode({"page": str(p), "per_page": str(per_page)})
        return f"<{base}{path}?{q}>"

    parts: list[str] = []
    if page < total_pages:
        parts.append(f'{link_url(page + 1)}; rel="next"')
    if page > 1:
        parts.append(f'{link_url(page - 1)}; rel="prev"')
    parts.append(f'{link_url(1)}; rel="first"')
    parts.append(f'{link_url(total_pages)}; rel="last"')
    return {"Link": ", ".join(parts)}
