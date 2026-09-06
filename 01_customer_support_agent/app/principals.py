import uuid
from dataclasses import dataclass
from enum import Enum


class PrincipalType(str, Enum):
    SERVICE = "service"
    CUSTOMER = "customer"


class AuthenticationMethod(str, Enum):
    N8N_SERVICE_KEY = "n8n_service_key"
    OIDC = "oidc"
    FIREBASE_ID_TOKEN = "firebase_id_token"


class Permission(str, Enum):
    SUPPORT_OPERATIONS = "support:operations"
    CUSTOMER_ORDER_ACCESS = "customer:orders"


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING = "pending"


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    principal_type: PrincipalType
    subject: str
    authentication_method: AuthenticationMethod
    permissions: frozenset[Permission] = frozenset()
    customer_id: uuid.UUID | None = None
    provider: str | None = None
    customer_status: CustomerStatus | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.principal_type, PrincipalType):
            raise ValueError("Unsupported authenticated principal type.")
        if not isinstance(self.authentication_method, AuthenticationMethod):
            raise ValueError("Unsupported authentication method.")
        if not isinstance(self.permissions, frozenset) or not all(
            isinstance(permission, Permission) for permission in self.permissions
        ):
            raise ValueError("Principal permissions must be typed and immutable.")
        if not self.subject or not self.subject.strip():
            raise ValueError("Authenticated principal subject is required.")

        if self.principal_type is PrincipalType.SERVICE:
            if self.authentication_method is not AuthenticationMethod.N8N_SERVICE_KEY:
                raise ValueError("Service principal authentication method is invalid.")
            if any(
                value is not None
                for value in (self.customer_id, self.provider, self.customer_status)
            ):
                raise ValueError("Service principals cannot contain customer identity.")
            return

        if self.principal_type is PrincipalType.CUSTOMER:
            if self.authentication_method not in {
                AuthenticationMethod.OIDC,
                AuthenticationMethod.FIREBASE_ID_TOKEN,
            }:
                raise ValueError("Customer principal authentication method is invalid.")
            if (
                self.customer_id is None
                or not self.provider
                or self.customer_status is None
            ):
                raise ValueError("Customer principal identity is incomplete.")
            return

        raise ValueError("Unsupported authenticated principal type.")


def create_n8n_service_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        principal_type=PrincipalType.SERVICE,
        subject="n8n",
        authentication_method=AuthenticationMethod.N8N_SERVICE_KEY,
        permissions=frozenset({Permission.SUPPORT_OPERATIONS}),
    )
