import unittest
import uuid

from tests import TEST_SERVICE_KEY  # noqa: F401 - initializes isolated test settings

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.authorization import get_customer_owned_order
from app.customer_identity import CustomerIdentityNotFound, resolve_customer_identity
from app.database import Base
from app.db_models import Customer, Order
from app.order_store import reset_orders
from app.principals import (
    AuthenticatedPrincipal,
    AuthenticationMethod,
    CustomerStatus,
    PrincipalType,
)


class TestCustomerIdentityAndAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, class_=Session)
        Base.metadata.create_all(cls.engine)
        with cls.SessionLocal() as db:
            reset_orders(db)
            db.commit()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def principal(self, customer_id: uuid.UUID) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            principal_type=PrincipalType.CUSTOMER,
            subject="already-verified-subject",
            authentication_method=AuthenticationMethod.OIDC,
            customer_id=customer_id,
            provider="demo",
            customer_status=CustomerStatus.ACTIVE,
        )

    def test_known_provider_subject_resolves_to_internal_uuid(self):
        with self.SessionLocal() as db:
            expected = db.scalar(
                select(Customer.id).where(Customer.auth_subject == "demo-ram")
            )
            resolved = resolve_customer_identity(
                db, provider="demo", subject="demo-ram"
            )
        self.assertEqual(resolved.customer_id, expected)
        self.assertIs(resolved.status, CustomerStatus.ACTIVE)

    def test_unknown_identity_is_not_provisioned(self):
        with self.SessionLocal() as db:
            before = db.scalar(select(func.count(Customer.id)))
            with self.assertRaises(CustomerIdentityNotFound):
                resolve_customer_identity(
                    db, provider="demo", subject="unknown-subject"
                )
            after = db.scalar(select(func.count(Customer.id)))
        self.assertEqual(after, before)

    def test_display_name_and_email_are_not_identity_inputs(self):
        with self.SessionLocal() as db:
            db.add(
                Customer(
                    auth_provider="other-provider",
                    auth_subject="other-subject",
                    display_name="demo-ram",
                    email="demo-ram",
                    status="active",
                )
            )
            db.commit()
            for provider, subject in (
                ("demo-ram", "demo-ram"),
                ("other-provider", "demo-ram"),
            ):
                with self.subTest(provider=provider, subject=subject):
                    with self.assertRaises(CustomerIdentityNotFound):
                        resolve_customer_identity(
                            db, provider=provider, subject=subject
                        )

    def test_owned_order_is_authorized_without_customer_name(self):
        with self.SessionLocal() as db:
            order = db.scalar(select(Order).where(Order.order_number == "DG-1001"))
            loaded = get_customer_owned_order(
                db,
                principal=self.principal(order.customer_id),
                order_number="DG-1001",
            )
            self.assertEqual(loaded.id, order.id)

    def test_foreign_and_nonexistent_orders_are_indistinguishable(self):
        with self.SessionLocal() as db:
            owner_id = db.scalar(
                select(Order.customer_id).where(Order.order_number == "DG-2005")
            )
            errors = []
            for order_number in ("DG-1001", "DG-9999"):
                with self.assertRaises(HTTPException) as raised:
                    get_customer_owned_order(
                        db,
                        principal=self.principal(owner_id),
                        order_number=order_number,
                    )
                errors.append((raised.exception.status_code, raised.exception.detail))
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(errors[0][0], 404)


if __name__ == "__main__":
    unittest.main()
