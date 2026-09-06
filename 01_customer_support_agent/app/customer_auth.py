from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.customer_identity import CustomerIdentityNotFound, resolve_customer_identity
from app.database import get_db
from app.firebase_auth import (
    FIREBASE_PROVIDER,
    FirebaseConfigurationError,
    FirebaseProviderUnavailableError,
    FirebaseTokenVerificationError,
    FirebaseTokenVerifier,
    get_firebase_token_verifier,
)
from app.principals import (
    AuthenticatedPrincipal,
    AuthenticationMethod,
    CustomerStatus,
    Permission,
    PrincipalType,
)


firebase_bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="FirebaseCustomerBearer",
)


def _customer_unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing customer credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _customer_forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Customer account is not authorized.",
    )


def require_firebase_customer(
    credentials: HTTPAuthorizationCredentials | None = Security(
        firebase_bearer_scheme
    ),
    db: Session = Depends(get_db),
    verifier: FirebaseTokenVerifier = Depends(get_firebase_token_verifier),
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _customer_unauthorized()

    try:
        verified_identity = verifier.verify(credentials.credentials)
    except (FirebaseConfigurationError, FirebaseProviderUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Customer authentication is unavailable.",
        ) from exc
    except FirebaseTokenVerificationError as exc:
        raise _customer_unauthorized() from exc

    try:
        customer = resolve_customer_identity(
            db,
            provider=FIREBASE_PROVIDER,
            subject=verified_identity.uid,
        )
    except CustomerIdentityNotFound as exc:
        raise _customer_forbidden() from exc

    if customer.status is not CustomerStatus.ACTIVE:
        raise _customer_forbidden()

    return AuthenticatedPrincipal(
        principal_type=PrincipalType.CUSTOMER,
        subject=verified_identity.uid,
        authentication_method=AuthenticationMethod.FIREBASE_ID_TOKEN,
        permissions=frozenset({Permission.CUSTOMER_ORDER_ACCESS}),
        customer_id=customer.customer_id,
        provider=FIREBASE_PROVIDER,
        customer_status=customer.status,
    )
