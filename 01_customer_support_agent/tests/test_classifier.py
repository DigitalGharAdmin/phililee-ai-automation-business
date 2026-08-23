import unittest

from app.classifier import classify_customer_message


class TestClassifierValidation(unittest.TestCase):
    def test_empty_message_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_customer_message("")


if __name__ == "__main__":
    unittest.main()