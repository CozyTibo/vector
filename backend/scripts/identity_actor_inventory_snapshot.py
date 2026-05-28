"""Print phase-0 identity actor signal inventory for one tenant."""

from __future__ import annotations

import argparse
import json
import uuid

from vector.domains.cortex.identity.inventory import build_actor_signal_inventory
from vector.infrastructure.db.session import session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description="Identity actor signal inventory snapshot.")
    parser.add_argument("--tenant", required=True, help="Tenant UUID")
    parser.add_argument("--limit", type=int, default=5000, help="Max actor rows to sample")
    args = parser.parse_args()
    tenant_id = uuid.UUID(args.tenant)
    with session_scope() as session:
        out = build_actor_signal_inventory(session, tenant_id=tenant_id, limit=args.limit)
    print(json.dumps(out, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()

