"""Add customer identity and nullable order ownership.

Revision ID: 20260903_0002
Revises: 20260901_0001
Create Date: 2026-09-03
"""

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260903_0002"
down_revision = "20260901_0001"
branch_labels = None
depends_on = None


DEMO_MAPPINGS = (
    (uuid.UUID("10000000-0000-4000-8000-000000000001"), "demo-ram", "Ram", "DG-1001"),
    (uuid.UUID("10000000-0000-4000-8000-000000000002"), "demo-sita", "Sita", "DG-2005"),
    (uuid.UUID("10000000-0000-4000-8000-000000000003"), "demo-hari", "Hari", "DG-3001"),
)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auth_provider", sa.String(length=64), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'pending')",
            name="customers_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "auth_provider",
            "auth_subject",
            name="customers_auth_provider_subject_key",
        ),
    )
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "orders_customer_id_fkey",
            "customers",
            ["customer_id"],
            ["id"],
        )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index(
        "ix_orders_customer_id_order_number",
        "orders",
        ["customer_id", "order_number"],
    )

    connection = op.get_bind()
    customers = sa.table(
        "customers",
        sa.column("id", sa.Uuid()),
        sa.column("auth_provider", sa.String()),
        sa.column("auth_subject", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("status", sa.String()),
    )
    orders = sa.table(
        "orders",
        sa.column("order_number", sa.String()),
        sa.column("customer_id", sa.Uuid()),
    )

    for customer_id, subject, display_name, order_number in DEMO_MAPPINGS:
        existing_id = connection.scalar(
            sa.select(customers.c.id).where(
                customers.c.auth_provider == "demo",
                customers.c.auth_subject == subject,
            )
        )
        if existing_id is None:
            connection.execute(
                customers.insert().values(
                    id=customer_id,
                    auth_provider="demo",
                    auth_subject=subject,
                    display_name=display_name,
                    status="active",
                )
            )
            existing_id = customer_id

        connection.execute(
            orders.update()
            .where(
                orders.c.order_number == order_number,
                orders.c.customer_id.is_(None),
            )
            .values(customer_id=existing_id)
        )


def downgrade() -> None:
    op.drop_index("ix_orders_customer_id_order_number", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("orders_customer_id_fkey", type_="foreignkey")
        batch_op.drop_column("customer_id")
    op.drop_table("customers")
