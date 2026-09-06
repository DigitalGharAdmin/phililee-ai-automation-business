import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import Customer
from app.principals import CustomerStatus


class CustomerIdentityNotFound(LookupError):
    """A verified external identity has no provisioned internal customer."""


@dataclass(frozen=True, slots=True)
class ResolvedCustomerIdentity:
    customer_id: uuid.UUID
    status: CustomerStatus


def resolve_customer_identity(
    db: Session,
    *,
    provider: str,
    subject: str,
) -> ResolvedCustomerIdentity:
    """Resolve an already-verified provider identity without provisioning it."""
    if not provider or not provider.strip() or not subject or not subject.strip():
        raise CustomerIdentityNotFound(
            "Authenticated customer identity is not provisioned."
        )

    row = db.execute(
        select(Customer.id, Customer.status).where(
            Customer.auth_provider == provider,
            Customer.auth_subject == subject,
        )
    ).one_or_none()
    if row is None:
        raise CustomerIdentityNotFound(
            "Authenticated customer identity is not provisioned."
        )

    return ResolvedCustomerIdentity(
        customer_id=row.id,
        status=CustomerStatus(row.status),
    )
