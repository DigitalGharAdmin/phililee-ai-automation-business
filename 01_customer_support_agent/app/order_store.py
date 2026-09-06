import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db_models import Customer, Order


DEMO_CUSTOMERS = {
    "ram": {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000001"),
        "auth_provider": "demo",
        "auth_subject": "demo-ram",
        "display_name": "Ram",
    },
    "sita": {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000002"),
        "auth_provider": "demo",
        "auth_subject": "demo-sita",
        "display_name": "Sita",
    },
    "hari": {
        "id": uuid.UUID("10000000-0000-4000-8000-000000000003"),
        "auth_provider": "demo",
        "auth_subject": "demo-hari",
        "display_name": "Hari",
    },
}

DEMO_ORDER_CUSTOMERS = {
    "DG-1001": "ram",
    "DG-2005": "sita",
    "DG-3001": "hari",
}


INITIAL_ORDERS = {
    "DG-1001": {
        "customer_name": "Ram",
        "status": "Processing",
        "estimated_delivery": "August 27, 2026",
        "tracking_number": "TRK-DG1001",
        "return_requested": False,
        "refund_requested": False,
    },
    "DG-2005": {
        "customer_name": "Sita",
        "status": "Out for Delivery",
        "estimated_delivery": "Today between 5 PM and 7 PM",
        "tracking_number": "TRK-DG2005",
        "return_requested": False,
        "refund_requested": False,
    },
    "DG-3001": {
        "customer_name": "Hari",
        "status": "Delivered",
        "estimated_delivery": "Delivered on August 24, 2026",
        "delivered_on": "August 24, 2026",
        "tracking_number": "TRK-DG3001",
        "return_requested": False,
        "refund_requested": False,
    },
}


def build_order_query(order_number: str, *, for_update: bool = False):
    statement = select(Order).where(Order.order_number == order_number)
    if for_update:
        statement = statement.with_for_update()
    return statement


def serialize_order(order: Order) -> dict:
    result = {
        "customer_name": order.customer_name,
        "status": order.status,
        "estimated_delivery": order.estimated_delivery,
        "tracking_number": order.tracking_number,
        "return_requested": order.return_requested,
        "refund_requested": order.refund_requested,
    }
    for optional_field in ("delivered_on", "return_id", "refund_id"):
        value = getattr(order, optional_field)
        if value is not None:
            result[optional_field] = value
    return result


def list_orders(db: Session) -> dict[str, dict]:
    records = db.scalars(select(Order).order_by(Order.order_number)).all()
    return {record.order_number: serialize_order(record) for record in records}


def reset_orders(db: Session) -> dict[str, dict]:
    db.execute(delete(Order))
    demo_customer_ids = {}
    for key, values in DEMO_CUSTOMERS.items():
        customer = db.scalar(
            select(Customer).where(
                Customer.auth_provider == values["auth_provider"],
                Customer.auth_subject == values["auth_subject"],
            )
        )
        if customer is None:
            customer = Customer(**values, status="active")
            db.add(customer)
            db.flush()
        demo_customer_ids[key] = customer.id

    db.add_all(
        Order(
            order_number=order_number,
            customer_id=demo_customer_ids[DEMO_ORDER_CUSTOMERS[order_number]],
            **values,
        )
        for order_number, values in INITIAL_ORDERS.items()
    )
    db.flush()
    return list_orders(db)
