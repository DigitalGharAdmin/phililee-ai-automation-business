"""Opt-in local PostgreSQL checks; unique fixtures are removed after each test."""
import os
import unittest
import uuid

from tests import TEST_SERVICE_KEY  # noqa: F401
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api import execute_support_operation
from app.authorization import get_customer_owned_order
from app.database import engine
from app.db_models import Customer, Order
from app.principals import AuthenticatedPrincipal, AuthenticationMethod, CustomerStatus, PrincipalType
from app.settings import SETTINGS


@unittest.skipUnless(os.environ.get('RUN_LOCAL_POSTGRES_TESTS') == '1', 'Opt-in local PostgreSQL tests')
class TestCustomerPostgresql(unittest.TestCase):
    def setUp(self):
        self.assertEqual(SETTINGS.app_environment, 'development')
        self.assertEqual(engine.dialect.name, 'postgresql')
        self.assertIn(engine.url.host, {'localhost', '127.0.0.1', '::1'})
        self.assertFalse(engine.url.query)
        self.customer_id = uuid.uuid4()
        # Unique non-public fixture number cannot collide with real/demo order numbers.
        self.number = 'TEST-' + uuid.uuid4().hex[:24]
        self.addCleanup(self.cleanup_rows)
        with Session(engine) as db, db.begin():
            db.add(Customer(id=self.customer_id, auth_provider='test-phase2d', auth_subject=uuid.uuid4().hex, status='active'))
            db.flush()
            db.add(Order(order_number=self.number, customer_id=self.customer_id, customer_name='Test fixture', status='Processing'))
        self.principal = AuthenticatedPrincipal(principal_type=PrincipalType.CUSTOMER, subject='test-only', authentication_method=AuthenticationMethod.FIREBASE_ID_TOKEN, customer_id=self.customer_id, provider='firebase', customer_status=CustomerStatus.ACTIVE)

    def cleanup_rows(self):
        with Session(engine) as db, db.begin():
            db.execute(delete(Order).where(Order.customer_id == self.customer_id))
            db.execute(delete(Customer).where(Customer.id == self.customer_id))

    def owned(self, db):
        return get_customer_owned_order(db, principal=self.principal, order_number=self.number, for_update=True)

    def test_mutation_persists_across_connections(self):
        with Session(engine, expire_on_commit=False) as db:
            row = self.owned(db)
            result = execute_support_operation(db, row, self.number, 'Cancel my order', 'cancel_order', None)
            self.assertTrue(result['success'])
        with Session(engine) as db:
            self.assertEqual(self.owned(db).status, 'Cancelled')

    def test_lock_contention_and_rollback(self):
        with Session(engine) as first:
            row = self.owned(first)
            with Session(engine) as second:
                with self.assertRaises(OperationalError):
                    second.scalar(select(Order).where(Order.order_number == self.number, Order.customer_id == self.customer_id).with_for_update(nowait=True))
                second.rollback()
            row.status = 'Cancelled'
            first.flush()
            first.rollback()
        with Session(engine) as db:
            self.assertEqual(self.owned(db).status, 'Processing')
