from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import Order
from app.principals import AuthenticatedPrincipal, Permission, PrincipalType


def require_permissions(
    principal: AuthenticatedPrincipal,
    required: Iterable[Permission],
) -> AuthenticatedPrincipal:
    if not frozenset(required).issubset(principal.permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The authenticated principal is not authorized for this operation.",
        )
    return principal


def get_customer_owned_order(
    db: Session,
    *,
    principal: AuthenticatedPrincipal,
    order_number: str,
    for_update: bool = False,
) -> Order:
    """Load an owned order without revealing whether a foreign order exists."""
    if principal.principal_type is not PrincipalType.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The authenticated principal is not authorized for this operation.",
        )

    statement = select(Order).where(
        Order.order_number == order_number,
        Order.customer_id == principal.customer_id,
    )
    if for_update:
        statement = statement.with_for_update()
    order = db.scalar(statement.execution_options(populate_existing=True))
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order
