"""Create a basic dev tenant + password user if the tenant slug is not taken."""

from __future__ import annotations

import os
import sys

from sqlalchemy.orm import sessionmaker

from vector.domains.identity_access.email_domain import email_domain_from_address
from vector.domains.identity_access.services.passwords import hash_password
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.infrastructure.db.session import get_engine


def main() -> None:
    slug = os.environ.get("SEED_TENANT_SLUG", "dev").strip()
    email = os.environ.get("SEED_USER_EMAIL", "dev@vector.local").strip().lower()
    password = os.environ.get("SEED_USER_PASSWORD", "changeme")
    company = os.environ.get("SEED_COMPANY_NAME", "Development").strip()

    if not slug or not email:
        print("SEED_TENANT_SLUG and SEED_USER_EMAIL must be non-empty", file=sys.stderr)
        sys.exit(1)

    engine = get_engine()
    factory = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    session = factory()
    try:
        if tenancy_repo.get_tenant_by_slug(session, slug):
            print(f"seed: tenant slug {slug!r} already exists — skipped")
            return
        domain = email_domain_from_address(email)
        if tenancy_repo.get_user_by_email(session, email):
            msg = (
                f"seed: user {email!r} exists but tenant slug {slug!r} "
                "does not — abort (resolve manually)"
            )
            print(msg, file=sys.stderr)
            sys.exit(1)
        ph = hash_password(password)
        user = User(email=email, full_name="Dev user", password_hash=ph)
        session.add(user)
        session.flush()
        tenant = Tenant(
            company_name=company or "Development",
            primary_email=email,
            email_domain=domain,
            slug=slug,
            status="active",
        )
        session.add(tenant)
        session.flush()
        session.add(
            TenantMembership(
                tenant_id=tenant.id,
                user_id=user.id,
                role="owner",
            ),
        )
        session.commit()
        print(f"seed: created tenant {slug!r} and user {email!r}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
