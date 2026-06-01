#!/usr/bin/env python3
"""Smoke-check Execution Surfaces admin read endpoints for a tenant.

Usage:
  TENANT_ID=... ADMIN_BASE_URL=http://127.0.0.1:8000 python scripts/execution_surfaces_smoke.py

Requires admin auth cookies/headers in your environment (run locally with dev server).
This script only documents expected HTTP 200 paths; it does not assert business outcomes.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

TENANT_ID = os.environ.get("TENANT_ID", "")
BASE = os.environ.get("ADMIN_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

PATHS = [
    "/admin/tenants/{tenant_id}/cortex/execution-surfaces/overview",
    "/admin/tenants/{tenant_id}/cortex/execution-surfaces/domains?limit=5",
    "/admin/tenants/{tenant_id}/cortex/execution-surfaces/people?limit=5",
    "/admin/tenants/{tenant_id}/cortex/execution-surfaces/work?limit=5",
    "/admin/tenants/{tenant_id}/cortex/execution-surfaces/activity?limit=5",
]


def main() -> int:
    if not TENANT_ID:
        print("Set TENANT_ID", file=sys.stderr)
        return 1
    failed = 0
    for template in PATHS:
        path = template.format(tenant_id=TENANT_ID)
        url = f"{BASE}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                ok = 200 <= resp.status < 300
        except urllib.error.HTTPError as exc:
            ok = False
            print(f"FAIL {exc.code} {url}")
            failed += 1
            continue
        except OSError as exc:
            print(f"SKIP {url} ({exc})")
            continue
        status = "OK" if ok else "FAIL"
        print(f"{status} {url}")
        if not ok:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
