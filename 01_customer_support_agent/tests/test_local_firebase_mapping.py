import unittest
from unittest.mock import Mock

from tests import TEST_SERVICE_KEY  # noqa: F401
from fastapi import HTTPException
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.database import Base
from app.db_models import Customer, Order
from app.firebase_auth import VerifiedFirebaseIdentity
from app.order_store import reset_orders
from scripts.provision_local_firebase import provision


class TestLocalFirebaseMapping(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        reset_orders(self.db)
        self.db.commit()
        self.verifier = Mock()
        self.verifier.verify.return_value = VerifiedFirebaseIdentity(uid="test-local-uid")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_separate_idempotent_mapping_preserves_demo_orders(self):
        before = self.db.execute(select(Order.order_number, Order.customer_id)).all()
        first = provision(self.db, "test-local-uid", "test-token", self.verifier)
        self.db.commit()
        second = provision(self.db, "test-local-uid", "test-token", self.verifier)
        self.assertEqual(first.customer_id, second.customer_id)
        self.assertEqual(before, self.db.execute(select(Order.order_number, Order.customer_id)).all())
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Customer)), 4)
        row = self.db.get(Customer, first.customer_id)
        self.assertIsNone(row.email)
        self.assertIsNone(row.display_name)
        self.assertNotIn("test-token", repr(first))

    def test_mismatched_uid_never_provisions(self):
        with self.assertRaises(ValueError):
            provision(self.db, "different-uid", "test-token", self.verifier)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Customer)), 3)

    def test_disabled_mapping_not_reactivated(self):
        self.db.add(Customer(auth_provider="firebase", auth_subject="test-local-uid", status="disabled"))
        self.db.commit()
        with self.assertRaises(HTTPException):
            provision(self.db, "test-local-uid", "test-token", self.verifier)
        self.db.rollback()
        self.assertEqual(self.db.scalar(select(Customer.status).where(Customer.auth_provider == "firebase")), "disabled")

    def test_second_verification_failure_rolls_back_insert(self):
        self.verifier.verify.side_effect = [VerifiedFirebaseIdentity(uid="test-local-uid"), ValueError("failed")]
        with self.assertRaises(ValueError):
            with self.db.begin():
                provision(self.db, "test-local-uid", "test-token", self.verifier)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Customer)), 3)
