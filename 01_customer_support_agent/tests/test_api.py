import os
import secrets
import unittest
from dataclasses import replace
from unittest.mock import patch

from tests import TEST_SERVICE_KEY

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import INITIAL_ORDERS, app
from app.database import Base, get_db
from app.db_models import Order
from app.settings import SETTINGS


class TestSupportApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_debug_setting = os.environ.get("ENABLE_DEBUG_ENDPOINTS")
        os.environ["ENABLE_DEBUG_ENDPOINTS"] = "true"
        cls.service_key = TEST_SERVICE_KEY
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            bind=cls.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
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
        if cls.original_debug_setting is None:
            os.environ.pop("ENABLE_DEBUG_ENDPOINTS", None)
        else:
            os.environ["ENABLE_DEBUG_ENDPOINTS"] = cls.original_debug_setting

    def setUp(self):
        response = self.client.post("/debug/reset")
        self.assertEqual(response.status_code, 200)

    def support(self, order_number, message, customer_name=None):
        customer_names = {
            "DG-1001": "Ram",
            "DG-2005": "Sita",
            "DG-3001": "Hari",
        }
        return self.client.post(
            "/support",
            json={
                "customer_name": (
                    customer_name
                    if customer_name is not None
                    else customer_names.get(order_number, "Test Customer")
                ),
                "order_number": order_number,
                "message": message,
            },
            headers={"Authorization": f"Bearer {self.service_key}"},
        )

    def set_order_status(self, order_number, status):
        with self.TestingSessionLocal() as db:
            order = db.scalar(select(Order).where(Order.order_number == order_number))
            order.status = status
            db.commit()

    def get_order_status(self, order_number):
        with self.TestingSessionLocal() as db:
            order = db.scalar(select(Order).where(Order.order_number == order_number))
            return order.status

    def test_support_requires_valid_n8n_service_authentication(self):
        payload = {
            "customer_name": "Ram",
            "order_number": "DG-1001",
            "message": "Track my order",
        }

        missing = self.client.post("/support", json=payload)
        malformed = self.client.post(
            "/support",
            json=payload,
            headers={"Authorization": "Basic not-a-bearer-credential"},
        )
        wrong_key = secrets.token_urlsafe(48)
        incorrect = self.client.post(
            "/support",
            json=payload,
            headers={"Authorization": f"Bearer {wrong_key}"},
        )
        valid = self.support("DG-1001", "Track my order")

        for response in (missing, malformed, incorrect):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")
            self.assertNotIn("N8N_SERVICE_KEY_SHA256", response.text)

        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["status"], "Processing")

    def test_debug_endpoints_follow_environment_mode(self):
        with patch(
            "app.settings.SETTINGS",
            replace(SETTINGS, app_environment="development", enable_debug_endpoints=True),
        ):
            self.assertEqual(self.client.post("/debug/reset").status_code, 200)
            self.assertEqual(self.client.get("/debug/orders").status_code, 200)
            self.assertEqual(
                self.client.get(
                    "/debug/intent", params={"message": "Track my order"}
                ).status_code,
                200,
            )
            self.assertEqual(
                self.support("DG-1001", "Track my order").status_code,
                200,
            )

        with patch(
            "app.settings.SETTINGS",
            replace(SETTINGS, app_environment="production", enable_debug_endpoints=False),
        ):
            for method, path in (
                (self.client.post, "/debug/reset"),
                (self.client.get, "/debug/orders"),
                (self.client.get, "/debug/intent?message=Track"),
                (self.client.get, "/debug/future-endpoint"),
            ):
                with self.subTest(path=path):
                    self.assertEqual(method(path).status_code, 404)

            support_response = self.support("DG-1001", "Track my order")
            self.assertEqual(support_response.status_code, 200)
            self.assertEqual(support_response.json()["status"], "Processing")

    def test_processing_order_tracking_uses_estimated_delivery(self):
        result = self.support("DG-1001", "Track my order").json()

        self.assertEqual(result["status"], "Processing")
        self.assertIn("Estimated delivery: August 27, 2026.", result["response"])
        self.assertNotIn("Delivered on:", result["response"])

    def test_out_for_delivery_tracking_uses_estimated_delivery(self):
        result = self.support("DG-2005", "Where is my order?").json()

        self.assertEqual(result["status"], "Out for Delivery")
        self.assertIn(
            "Estimated delivery: Today between 5 PM and 7 PM.",
            result["response"],
        )
        self.assertNotIn("Delivered on:", result["response"])

    def test_delivered_order_tracking_uses_delivered_on(self):
        result = self.support("DG-3001", "Order status").json()

        self.assertEqual(result["status"], "Delivered")
        self.assertEqual(result["delivered_on"], "August 24, 2026")
        self.assertIn("Delivered on: August 24, 2026.", result["response"])
        self.assertNotIn("Estimated delivery:", result["response"])

    def test_return_requested_tracking_preserves_history_and_return_id(self):
        return_result = self.support("DG-3001", "Return my order").json()
        tracking_result = self.support("DG-3001", "Track my order").json()

        self.assertTrue(return_result["success"])
        self.assertEqual(tracking_result["status"], "Return Requested")
        self.assertEqual(tracking_result["return_id"], "RET-3001")
        self.assertIn("Delivered on: August 24, 2026.", tracking_result["response"])
        self.assertIn("Return ID: RET-3001.", tracking_result["response"])
        self.assertNotIn("Estimated delivery:", tracking_result["response"])

    def test_refund_requested_tracking_preserves_history_and_refund_id(self):
        refund_result = self.support("DG-3001", "Refund my order").json()
        tracking_result = self.support("DG-3001", "Track my order").json()

        self.assertTrue(refund_result["success"])
        self.assertEqual(tracking_result["status"], "Refund Requested")
        self.assertEqual(tracking_result["refund_id"], "REF-3001")
        self.assertIn("Delivered on: August 24, 2026.", tracking_result["response"])
        self.assertIn("Refund ID: REF-3001.", tracking_result["response"])
        self.assertNotIn("Estimated delivery:", tracking_result["response"])

    def test_existing_cancellation_return_and_refund_rules(self):
        cancellation = self.support("DG-1001", "Cancel my order").json()
        duplicate_cancellation = self.support("DG-1001", "Cancel my order").json()
        early_return = self.support("DG-2005", "Return my order").json()
        early_refund = self.support("DG-2005", "Refund my order").json()

        self.assertTrue(cancellation["success"])
        self.assertEqual(cancellation["status"], "Cancelled")
        self.assertFalse(duplicate_cancellation["success"])
        self.assertFalse(early_return["success"])
        self.assertFalse(early_refund["success"])

    def test_existing_return_refund_conflicts_and_duplicates(self):
        first_return = self.support("DG-3001", "Return my order").json()
        duplicate_return = self.support("DG-3001", "Return my order").json()
        refund_conflict = self.support("DG-3001", "Refund my order").json()

        self.assertTrue(first_return["success"])
        self.assertFalse(duplicate_return["success"])
        self.assertFalse(refund_conflict["success"])

        self.client.post("/debug/reset")
        first_refund = self.support("DG-3001", "Refund my order").json()
        duplicate_refund = self.support("DG-3001", "Refund my order").json()
        return_conflict = self.support("DG-3001", "Return my order").json()

        self.assertTrue(first_refund["success"])
        self.assertFalse(duplicate_refund["success"])
        self.assertFalse(return_conflict["success"])

    def test_negated_state_changes_do_not_mutate(self):
        scenarios = (
            ("DG-1001", "Do not cancel my order.", "Processing"),
            ("DG-1001", "I don't want to cancel.", "Processing"),
            ("DG-3001", "Please don't refund my order.", "Delivered"),
            ("DG-3001", "I do not want to return it.", "Delivered"),
        )
        for order_number, message, initial_status in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                result = self.support(order_number, message)
                state = self.client.get("/debug/orders").json()[order_number]

                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["intent"], "general_support")
                self.assertEqual(state["status"], initial_status)

    def test_additional_informational_questions_do_not_mutate(self):
        scenarios = (
            ("DG-1001", "What happens if I cancel?", "Processing"),
            ("DG-3001", "Am I eligible for a refund?", "Delivered"),
        )
        for order_number, message, initial_status in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                result = self.support(order_number, message)
                state = self.client.get("/debug/orders").json()[order_number]

                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["intent"], "general_support")
                self.assertEqual(state["status"], initial_status)

    def test_informational_questions_do_not_mutate(self):
        scenarios = (
            ("DG-1001", "Can I cancel my order?", "Processing"),
            ("DG-3001", "Can I return my order?", "Delivered"),
            ("DG-3001", "Can I get a refund?", "Delivered"),
        )
        for order_number, message, initial_status in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                result = self.support(order_number, message)
                state = self.client.get("/debug/orders").json()[order_number]

                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["intent"], "general_support")
                self.assertEqual(state["status"], initial_status)

    def test_multiple_intents_require_clarification_without_mutation(self):
        scenarios = (
            ("DG-3001", "Cancel and refund my order."),
            ("DG-3001", "Track and refund my order."),
        )
        for order_number, message in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                result = self.support(order_number, message)
                state = self.client.get("/debug/orders").json()[order_number]

                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["intent"], "general_support")
                self.assertIn("choose one", result.json()["response"].lower())
                self.assertEqual(state, INITIAL_ORDERS[order_number])

    def test_explicit_state_changing_requests_still_succeed(self):
        scenarios = (
            ("DG-1001", "Please cancel my order.", "Cancelled"),
            ("DG-3001", "Please return my order.", "Return Requested"),
            ("DG-3001", "Please refund my order.", "Refund Requested"),
        )
        for order_number, message, expected_status in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                result = self.support(order_number, message)

                self.assertEqual(result.status_code, 200)
                self.assertTrue(result.json()["success"])
                self.assertEqual(result.json()["status"], expected_status)

    def test_customer_name_is_required(self):
        for customer_name in ("", "   "):
            with self.subTest(customer_name=repr(customer_name)):
                result = self.support(
                    "DG-1001", "Track my order", customer_name=customer_name
                )
                self.assertEqual(result.status_code, 400)
                self.assertFalse(result.json()["success"])
                self.assertEqual(
                    result.json()["error"]["type"], "invalid_customer_name"
                )

        for payload in (
            {"order_number": "DG-1001", "message": "Track my order"},
            {
                "customer_name": None,
                "order_number": "DG-1001",
                "message": "Track my order",
            },
        ):
            with self.subTest(payload=payload):
                result = self.client.post(
                    "/support",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.service_key}"},
                )
                self.assertEqual(result.status_code, 422)

    def test_wrong_customer_is_rejected_without_order_details(self):
        result = self.support(
            "DG-1001", "Track my order", customer_name="Wrong Person"
        )
        body = result.json()

        self.assertEqual(result.status_code, 403)
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["type"], "customer_order_mismatch")
        for sensitive_field in (
            "status",
            "estimated_delivery",
            "delivered_on",
            "tracking_number",
            "return_id",
            "refund_id",
        ):
            self.assertNotIn(sensitive_field, body)

    def test_customer_name_comparison_is_trimmed_and_case_insensitive(self):
        for customer_name in ("  Ram  ", "rAm"):
            with self.subTest(customer_name=customer_name):
                result = self.support(
                    "DG-1001", "Track my order", customer_name=customer_name
                )
                self.assertEqual(result.status_code, 200)
                self.assertTrue(result.json()["success"])

    def test_order_number_validation_remains_enforced(self):
        malformed = self.support("not-an-order", "Track my order")
        unknown = self.support("DG-9999", "Track my order")

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()["error"]["type"], "invalid_order_number")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.json()["error"]["type"], "order_not_found")

    def test_order_number_token_normalization(self):
        scenarios = (
            ("DG-3001", "Hari", "Track my order", "DG-3001"),
            ("  dg-3001  ", "Hari", "Track my order", "DG-3001"),
            (
                "DG-3001 CAN I RETURN MY ORDER?",
                "Hari",
                "Return my order",
                "DG-3001",
            ),
            (
                "DG-2005 REFUND MY ORDER",
                "Sita",
                "Refund my order",
                "DG-2005",
            ),
            ("Please use DG-2005", "Sita", "Track my order", "DG-2005"),
        )
        for supplied_order, customer_name, message, expected_order in scenarios:
            with self.subTest(supplied_order=supplied_order):
                self.client.post("/debug/reset")
                result = self.support(
                    supplied_order,
                    message,
                    customer_name=customer_name,
                )

                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["order_number"], expected_order)

    def test_order_number_token_rejects_missing_malformed_and_ambiguous_values(self):
        invalid_values = (
            "no order number here",
            "DG-12",
            "DG-ABCDE",
            "DG3001",
            "DG-3001 and DG-2005",
            "DG-3001 DG-3001",
        )
        for supplied_order in invalid_values:
            with self.subTest(supplied_order=supplied_order):
                result = self.support(
                    supplied_order,
                    "Track my order",
                    customer_name="Hari",
                )

                self.assertEqual(result.status_code, 400)
                self.assertEqual(
                    result.json()["error"]["type"], "invalid_order_number"
                )

    def test_extracted_unknown_order_keeps_not_found_behavior(self):
        result = self.support(
            "Please use DG-9999",
            "Track my order",
            customer_name="Unknown Customer",
        )

        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.json()["order_number"], "DG-9999")
        self.assertEqual(result.json()["error"]["type"], "order_not_found")

    def test_cancelled_tracking_has_no_delivery_promise(self):
        cancellation = self.support("DG-1001", "Cancel my order")
        tracking = self.support("DG-1001", "Track my order")
        body = tracking.json()

        self.assertTrue(cancellation.json()["success"])
        self.assertEqual(tracking.status_code, 200)
        self.assertEqual(body["status"], "Cancelled")
        self.assertIsNone(body["estimated_delivery"])
        self.assertIsNone(body["tracking_number"])
        self.assertNotIn("Estimated delivery", body["response"])
        self.assertNotIn("August 27, 2026", body["response"])

    def test_cancellation_state_transition_allowlist(self):
        scenarios = (
            ("DG-1001", "Processing", True),
            ("DG-2005", "Out for Delivery", False),
            ("DG-3001", "Delivered", False),
        )
        for order_number, status, should_succeed in scenarios:
            with self.subTest(status=status):
                self.client.post("/debug/reset")
                result = self.support(order_number, "Cancel my order").json()
                self.assertEqual(result["success"], should_succeed)

        self.set_order_status("DG-1001", "Unknown State")
        result = self.support("DG-1001", "Cancel my order").json()
        self.assertFalse(result["success"])
        self.assertEqual(self.get_order_status("DG-1001"), "Unknown State")

    def test_return_state_transition_allowlist(self):
        scenarios = (
            ("DG-3001", "Delivered", True),
            ("DG-1001", "Processing", False),
            ("DG-2005", "Out for Delivery", False),
        )
        for order_number, status, should_succeed in scenarios:
            with self.subTest(status=status):
                self.client.post("/debug/reset")
                result = self.support(order_number, "Return my order").json()
                self.assertEqual(result["success"], should_succeed)

        self.client.post("/debug/reset")
        self.support("DG-1001", "Cancel my order")
        self.assertFalse(self.support("DG-1001", "Return my order").json()["success"])

        self.client.post("/debug/reset")
        self.support("DG-3001", "Refund my order")
        self.assertFalse(self.support("DG-3001", "Return my order").json()["success"])

        self.client.post("/debug/reset")
        self.set_order_status("DG-3001", "Unknown State")
        result = self.support("DG-3001", "Return my order").json()
        self.assertFalse(result["success"])
        self.assertEqual(self.get_order_status("DG-3001"), "Unknown State")

    def test_refund_state_transition_allowlist(self):
        scenarios = (
            ("DG-3001", "Delivered", True),
            ("DG-1001", "Processing", False),
            ("DG-2005", "Out for Delivery", False),
        )
        for order_number, status, should_succeed in scenarios:
            with self.subTest(status=status):
                self.client.post("/debug/reset")
                result = self.support(order_number, "Refund my order").json()
                self.assertEqual(result["success"], should_succeed)

        self.client.post("/debug/reset")
        self.support("DG-1001", "Cancel my order")
        self.assertFalse(self.support("DG-1001", "Refund my order").json()["success"])

        self.client.post("/debug/reset")
        self.support("DG-3001", "Return my order")
        self.assertFalse(self.support("DG-3001", "Refund my order").json()["success"])

        self.client.post("/debug/reset")
        self.set_order_status("DG-3001", "Unknown State")
        result = self.support("DG-3001", "Refund my order").json()
        self.assertFalse(result["success"])
        self.assertEqual(self.get_order_status("DG-3001"), "Unknown State")

    def test_reset_fully_restores_state_after_each_mutation(self):
        scenarios = (
            ("DG-1001", "Cancel my order"),
            ("DG-3001", "Return my order"),
            ("DG-3001", "Refund my order"),
        )
        for order_number, message in scenarios:
            with self.subTest(message=message):
                self.client.post("/debug/reset")
                self.assertTrue(self.support(order_number, message).json()["success"])
                reset = self.client.post("/debug/reset")

                self.assertEqual(reset.status_code, 200)
                self.assertEqual(reset.json()["orders"], INITIAL_ORDERS)
                self.assertEqual(
                    self.client.get("/debug/orders").json(), INITIAL_ORDERS
                )
                self.assertNotIn("return_id", reset.json()["orders"]["DG-3001"])
                self.assertNotIn("refund_id", reset.json()["orders"]["DG-3001"])


if __name__ == "__main__":
    unittest.main()
