import os
import tempfile
import unittest
from pathlib import Path

from tests import TEST_SERVICE_KEY

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.api import app
from app.database import Base, get_db
from app.db_models import Customer, Order
from app.order_store import DEMO_CUSTOMERS, build_order_query


class TestDatabasePersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_debug_setting = os.environ.get("ENABLE_DEBUG_ENDPOINTS")
        os.environ["ENABLE_DEBUG_ENDPOINTS"] = "true"
        cls.service_key = TEST_SERVICE_KEY
        cls.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_directory.name) / "orders.db"
        cls.engine = create_engine(f"sqlite+pysqlite:///{database_path}")

        @event.listens_for(cls.engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        cls.SessionLocal = sessionmaker(
            bind=cls.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(cls.engine)

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()
        cls.temp_directory.cleanup()
        if cls.original_debug_setting is None:
            os.environ.pop("ENABLE_DEBUG_ENDPOINTS", None)
        else:
            os.environ["ENABLE_DEBUG_ENDPOINTS"] = cls.original_debug_setting

    def setUp(self):
        response = self.client.post("/debug/reset")
        self.assertEqual(response.status_code, 200)

    def support(self, customer_name, order_number, message):
        return self.client.post(
            "/support",
            json={
                "customer_name": customer_name,
                "order_number": order_number,
                "message": message,
            },
            headers={"Authorization": f"Bearer {self.service_key}"},
        )

    def load_order(self, order_number):
        with self.SessionLocal() as db:
            return db.scalar(
                select(Order).where(Order.order_number == order_number)
            )

    def test_seeded_orders_exist_in_database(self):
        with self.SessionLocal() as db:
            orders = db.scalars(select(Order).order_by(Order.order_number)).all()

        self.assertEqual(
            [(order.order_number, order.status) for order in orders],
            [
                ("DG-1001", "Processing"),
                ("DG-2005", "Out for Delivery"),
                ("DG-3001", "Delivered"),
            ],
        )

    def test_customer_schema_constraints_indexes_and_relationship(self):
        inspector = inspect(self.engine)
        self.assertIn("customers", inspector.get_table_names())
        self.assertIn(
            "customer_id",
            {column["name"] for column in inspector.get_columns("orders")},
        )
        self.assertIn(
            "ix_orders_customer_id",
            {index["name"] for index in inspector.get_indexes("orders")},
        )
        self.assertIn(
            "ix_orders_customer_id_order_number",
            {index["name"] for index in inspector.get_indexes("orders")},
        )

        with self.SessionLocal() as db:
            customer = db.scalar(
                select(Customer).where(Customer.auth_subject == "demo-ram")
            )
            order = db.scalar(select(Order).where(Order.order_number == "DG-1001"))
            self.assertEqual(order.customer_id, customer.id)
            self.assertEqual(order.customer.auth_subject, "demo-ram")
            self.assertIn(order, customer.orders)

    def test_customer_uuid_and_allowed_statuses(self):
        with self.SessionLocal() as db:
            customer = Customer(
                auth_provider="test",
                auth_subject="pending-customer",
                status="pending",
            )
            db.add(customer)
            db.commit()
            self.assertIsNotNone(customer.id)
            self.assertEqual(customer.id.version, 4)

    def test_customer_provider_subject_is_unique(self):
        with self.SessionLocal() as db:
            db.add_all(
                [
                    Customer(auth_provider="test", auth_subject="duplicate", status="active"),
                    Customer(auth_provider="test", auth_subject="duplicate", status="disabled"),
                ]
            )
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_invalid_customer_status_is_rejected(self):
        with self.SessionLocal() as db:
            db.add(
                Customer(
                    auth_provider="test",
                    auth_subject="invalid-status",
                    status="unknown",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_demo_reset_is_idempotent_and_maps_explicit_orders(self):
        self.client.post("/debug/reset")
        self.client.post("/debug/reset")
        with self.SessionLocal() as db:
            customers = db.scalars(
                select(Customer).where(Customer.auth_provider == "demo")
            ).all()
            self.assertEqual(len(customers), 3)
            by_subject = {customer.auth_subject: customer for customer in customers}
            expected = {
                "DG-1001": "demo-ram",
                "DG-2005": "demo-sita",
                "DG-3001": "demo-hari",
            }
            for order_number, subject in expected.items():
                order = db.scalar(
                    select(Order).where(Order.order_number == order_number)
                )
                self.assertEqual(order.customer_id, by_subject[subject].id)
                self.assertEqual(
                    order.customer_id,
                    DEMO_CUSTOMERS[subject.removeprefix("demo-")]["id"],
                )

    def test_customer_foreign_key_is_enforced(self):
        with self.SessionLocal() as db:
            order = db.scalar(select(Order).where(Order.order_number == "DG-1001"))
            order.customer_id = __import__("uuid").uuid4()
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_tracking_reads_state_written_by_another_session(self):
        with self.SessionLocal() as db:
            order = db.scalar(
                select(Order).where(Order.order_number == "DG-1001")
            )
            order.status = "Cancelled"
            db.commit()

        result = self.support("Ram", "DG-1001", "Track my order")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["status"], "Cancelled")

    def test_customer_id_persists_and_survives_state_mutation(self):
        with self.SessionLocal() as db:
            original_customer_id = db.scalar(
                select(Order.customer_id).where(Order.order_number == "DG-1001")
            )

        result = self.support("Ram", "DG-1001", "Cancel my order")
        self.assertEqual(result.status_code, 200)

        with self.SessionLocal() as db:
            order = db.scalar(select(Order).where(Order.order_number == "DG-1001"))
            self.assertEqual(order.customer_id, original_customer_id)

    def test_mutations_persist_across_separate_sessions(self):
        scenarios = (
            ("Ram", "DG-1001", "Cancel my order", "Cancelled", None, None),
            (
                "Hari",
                "DG-3001",
                "Return my order",
                "Return Requested",
                "RET-3001",
                None,
            ),
            (
                "Hari",
                "DG-3001",
                "Refund my order",
                "Refund Requested",
                None,
                "REF-3001",
            ),
        )
        for customer, order_number, message, status, return_id, refund_id in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                result = self.support(customer, order_number, message)
                order = self.load_order(order_number)

                self.assertTrue(result.json()["success"])
                self.assertEqual(order.status, status)
                self.assertEqual(order.return_id, return_id)
                self.assertEqual(order.refund_id, refund_id)

    def test_duplicates_and_conflicts_use_reloaded_database_state(self):
        scenarios = (
            ("Ram", "DG-1001", "Cancel my order", "Cancel my order"),
            ("Hari", "DG-3001", "Return my order", "Return my order"),
            ("Hari", "DG-3001", "Refund my order", "Refund my order"),
            ("Hari", "DG-3001", "Return my order", "Refund my order"),
            ("Hari", "DG-3001", "Refund my order", "Return my order"),
        )
        for customer, order_number, first_message, second_message in scenarios:
            with self.subTest(first=first_message, second=second_message):
                self.client.post("/debug/reset")
                first = self.support(customer, order_number, first_message)
                second = self.support(customer, order_number, second_message)

                self.assertTrue(first.json()["success"])
                self.assertFalse(second.json()["success"])

    def test_failed_transaction_rolls_back_all_state(self):
        with self.SessionLocal() as db:
            try:
                with db.begin():
                    order = db.scalar(
                        build_order_query("DG-3001", for_update=True)
                    )
                    order.status = "Return Requested"
                    order.return_requested = True
                    order.return_id = "RET-3001"
                    raise RuntimeError("simulated transaction failure")
            except RuntimeError:
                pass

        restored = self.load_order("DG-3001")
        self.assertEqual(restored.status, "Delivered")
        self.assertFalse(restored.return_requested)
        self.assertIsNone(restored.return_id)

    def test_state_change_query_is_postgresql_row_locked(self):
        statement = build_order_query("DG-3001", for_update=True)
        compiled = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        self.assertIn("FOR UPDATE", compiled)
