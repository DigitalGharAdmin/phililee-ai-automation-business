import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.api import health, ready


class TestOperationalEndpoints(unittest.TestCase):
    def test_health_is_minimal(self):
        self.assertEqual(health(), {"status": "ok"})

    def test_readiness_passes_with_database(self):
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = 1
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection
        with patch("app.database.engine", engine):
            self.assertEqual(asyncio.run(ready()), {"status": "ready"})
        connection.execute.assert_called_once()

    def test_readiness_failure_is_safe(self):
        engine = MagicMock()
        engine.connect.side_effect = RuntimeError("database secret detail")
        with patch("app.database.engine", engine):
            response = asyncio.run(ready())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"secret", response.body)
