"""Rebuild identity v1 substrate from canon actor entities."""

from __future__ import annotations

import argparse
import json
import uuid

from vector.domains.cortex.identity.materialize import rebuild_identities_for_tenant
from vector.infrastructure.db.session import session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild identities for one tenant.")
    parser.add_argument("--tenant", required=True, help="Tenant UUID")
    parser.add_argument("--batch-limit", type=int, default=1000)
    parser.add_argument("--resolver-version", type=int, default=None)
    args = parser.parse_args()
    tenant_id = uuid.UUID(args.tenant)
    with session_scope() as session:
        out = rebuild_identities_for_tenant(
            session,
            tenant_id=tenant_id,
            batch_limit=args.batch_limit,
            resolver_version=args.resolver_version,
        )
        session.commit()
    print(json.dumps(out, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()

