"""Explicit local provisioning only; never imported by application routes."""

import json
import logging
import sys
from dataclasses import fields


def provision(db, uid, token, verifier):
    from fastapi.security import HTTPAuthorizationCredentials
    from sqlalchemy import select
    from app.customer_auth import require_firebase_customer
    from app.db_models import Customer
    from app.principals import AuthenticationMethod, CustomerStatus, PrincipalType

    if not isinstance(uid, str) or not uid.strip() or len(uid) > 128:
        raise ValueError("Invalid input")
    if verifier.verify(token).uid != uid:
        raise ValueError("Identity mismatch")
    customer = db.scalar(select(Customer).where(
        Customer.auth_provider == "firebase", Customer.auth_subject == uid
    ))
    if customer is None:
        customer = Customer(auth_provider="firebase", auth_subject=uid, status="active")
        db.add(customer)
        db.flush()
    principal = require_firebase_customer(
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        db=db, verifier=verifier,
    )
    if not (
        principal.customer_id == customer.id
        and principal.customer_id is not None
        and principal.subject == uid
        and principal.principal_type is PrincipalType.CUSTOMER
        and principal.customer_status is CustomerStatus.ACTIVE
        and principal.provider == "firebase"
        and principal.authentication_method is AuthenticationMethod.FIREBASE_ID_TOKEN
        and {field.name for field in fields(principal)} == {
            "principal_type", "subject", "authentication_method", "permissions",
            "customer_id", "provider", "customer_status",
        }
        and all(getattr(principal, field.name) != token for field in fields(principal))
    ):
        raise ValueError("Principal verification failed")
    return principal


def main():
    # Suppress third-party diagnostics, including SQL parameters and credentials.
    previous_logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        from sqlalchemy.engine import make_url
        from app.settings import SETTINGS
        url = make_url(SETTINGS.database_url)
        if (SETTINGS.app_environment != "development"
                or url.get_backend_name() != "postgresql"
                or url.host not in {"localhost", "127.0.0.1", "::1"}
                or url.query):
            raise ValueError("Local development PostgreSQL required")
        from app.database import SessionLocal
        from app.firebase_auth import FirebaseTokenVerifier
        payload = json.loads(sys.stdin.read(32769))
        with SessionLocal.begin() as db:
            provision(db, payload["uid"], payload["token"], FirebaseTokenVerifier())
        print("LOCAL_FIREBASE_MAPPING=PASS IDENTITY_RESOLUTION=PASS TOKEN_STORED=NO")
        return 0
    except Exception:
        # Never render exceptions: driver/provider errors can include sensitive input.
        print("LOCAL_FIREBASE_MAPPING=FAIL (no credentials printed; transaction rolled back)")
        return 1
    finally:
        logging.disable(previous_logging_disable)


if __name__ == "__main__":
    sys.exit(main())
