"""init all models (users, centres, tests, offerings, bookings, payments, webhook_events).

Revision ID: c1a7e6f2b804
Revises:
Create Date: 2026-09-26

Postgres-targeted baseline covering every table in app.models. Types were
chosen to work on both PostgreSQL (deploy target) and SQLite (hermetic tests):
NUMERIC(10, 2) prices, timezone-aware datetimes, generic JSON payload.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1a7e6f2b804"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # NOTE: email is unique via the unique index below (Column(unique=True,
    # index=True) renders as a unique Index, not a UniqueConstraint).
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "centres",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_centres_location", "centres", ["location"], unique=False)

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tests_name"),
    )

    op.create_table(
        "offerings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("centre_id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("centre_id", "test_id", name="uq_offering_centre_test"),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("centre_id", sa.Integer(), nullable=False),
        sa.Column("appointment_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["centre_id"], ["centres.id"]),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_reference", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # NOTE: provider_reference uniqueness comes from the unique index below.
    op.create_index(
        "ix_payments_provider_reference", "payments", ["provider_reference"], unique=True
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("provider_reference", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # NOTE: event_id uniqueness comes from the unique index below.
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_webhook_events_event_id", table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_index("ix_payments_provider_reference", table_name="payments")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("offerings")
    op.drop_table("tests")
    op.drop_index("ix_centres_location", table_name="centres")
    op.drop_table("centres")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
