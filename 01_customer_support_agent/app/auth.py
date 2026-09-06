import hashlib
import hmac

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.authorization import require_permissions
from app.principals import (
    AuthenticatedPrincipal,
    Permission,
    create_n8n_service_principal,
)
from app.settings import SETTINGS

bearer_scheme = HTTPBearer(auto_error=False)


def require_n8n_service(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedPrincipal:
    supplied_key = credentials.credentials if credentials is not None else ""
    supplied_digest = hashlib.sha256(supplied_key.encode("utf-8")).hexdigest()

    key_is_valid = hmac.compare_digest(
        supplied_digest, SETTINGS.n8n_service_key_sha256
    )
    scheme_is_valid = (
        credentials is not None and credentials.scheme.casefold() == "bearer"
    )

    if not scheme_is_valid or not key_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_n8n_service_principal()


def require_n8n_support_service(
    principal: AuthenticatedPrincipal = Depends(require_n8n_service),
) -> AuthenticatedPrincipal:
    return require_permissions(principal, {Permission.SUPPORT_OPERATIONS})
