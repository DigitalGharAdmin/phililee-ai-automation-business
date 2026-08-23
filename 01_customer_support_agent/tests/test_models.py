import unittest

from app.models import Intent, Priority, SupportClassification


class TestSupportClassification(unittest.TestCase):
    def test_valid_classification(self):
        result = SupportClassification(
            intent=Intent.ORDER_STATUS,
            priority=Priority.LOW,
            requires_human=False,
            customer_request="Customer wants to know where the order is.",
        )

        self.assertEqual(result.intent, Intent.ORDER_STATUS)
        self.assertEqual(result.priority, Priority.LOW)
        self.assertFalse(result.requires_human)


if __name__ == "__main__":
    unittest.main()