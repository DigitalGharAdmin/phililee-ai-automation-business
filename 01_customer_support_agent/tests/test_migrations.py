import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


class TestIdentityMigration(unittest.TestCase):
    def alembic_config(self, database_url: str) -> Config:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["database_url"] = database_url
        return config

    def test_upgrade_backfill_unknown_order_and_downgrade_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            database_url = f"sqlite+pysqlite:///{Path(directory) / 'migration.db'}"
            config = self.alembic_config(database_url)
            command.upgrade(config, "20260901_0001")

            engine = create_engine(database_url)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO orders "
                        "(order_number, customer_name, status, return_requested, refund_requested) "
                        "VALUES (:number, :name, :status, false, false)"
                    ),
                    [
                        {"number": "DG-1001", "name": "Ram", "status": "Processing"},
                        {"number": "DG-2005", "name": "Sita", "status": "Out for Delivery"},
                        {"number": "DG-3001", "name": "Hari", "status": "Delivered"},
                        {"number": "DG-9999", "name": "Ram", "status": "Processing"},
                    ],
                )

            command.upgrade(config, "head")
            with engine.connect() as connection:
                rows = connection.execute(
                    text(
                        "SELECT order_number, customer_id FROM orders "
                        "ORDER BY order_number"
                    )
                ).all()
                customers = connection.execute(
                    text(
                        "SELECT auth_subject FROM customers "
                        "WHERE auth_provider = 'demo'"
                    )
                ).all()
            self.assertEqual(len(customers), 3)
            self.assertTrue(all(customer_id for _, customer_id in rows[:3]))
            self.assertIsNone(rows[3].customer_id)
            command.check(config)

            command.downgrade(config, "20260901_0001")
            inspector = inspect(engine)
            self.assertNotIn("customers", inspector.get_table_names())
            self.assertNotIn(
                "customer_id",
                {column["name"] for column in inspector.get_columns("orders")},
            )
            with engine.connect() as connection:
                self.assertEqual(
                    connection.scalar(text("SELECT count(*) FROM orders")), 4
                )
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
