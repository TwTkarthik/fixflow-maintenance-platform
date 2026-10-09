"""initial database schema

Revision ID: e98ccb2cbf89
Revises:
Create Date: 2026-10-09 23:55:18.348834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e98ccb2cbf89'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    user_role = sa.Enum(
        "administrator",
        "manager",
        "technician",
        name="user_role",
        native_enum=False,
        create_constraint=True,
        length=13,
    )
    asset_status = sa.Enum(
        "active",
        "deactivated",
        name="asset_status",
        native_enum=False,
        create_constraint=True,
        length=11,
    )
    work_order_priority = sa.Enum(
        "low",
        "medium",
        "high",
        "critical",
        name="work_order_priority",
        native_enum=False,
        create_constraint=True,
        length=8,
    )
    work_order_status = sa.Enum(
        "open",
        "assigned",
        "in_progress",
        "on_hold",
        "completed",
        "cancelled",
        name="work_order_status",
        native_enum=False,
        create_constraint=True,
        length=11,
    )
    update_type = sa.Enum(
        "status_change",
        "note",
        "assignment",
        name="work_order_update_type",
        native_enum=False,
        create_constraint=True,
        length=13,
    )
    update_status_from = sa.Enum(
        "open",
        "assigned",
        "in_progress",
        "on_hold",
        "completed",
        "cancelled",
        name="work_order_update_from_status",
        native_enum=False,
        create_constraint=True,
        length=11,
    )
    update_status_to = sa.Enum(
        "open",
        "assigned",
        "in_progress",
        "on_hold",
        "completed",
        "cancelled",
        name="work_order_update_to_status",
        native_enum=False,
        create_constraint=True,
        length=11,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(full_name)) > 0", name="users_full_name_not_blank"),
        sa.CheckConstraint("length(trim(email)) > 0", name="users_email_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_role_is_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("serial_number", sa.String(length=160), nullable=True),
        sa.Column("manufacturer", sa.String(length=160), nullable=True),
        sa.Column("model", sa.String(length=160), nullable=True),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", asset_status, server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(asset_code)) > 0", name="assets_asset_code_not_blank"),
        sa.CheckConstraint("length(trim(name)) > 0", name="assets_name_not_blank"),
        sa.CheckConstraint("length(trim(category)) > 0", name="assets_category_not_blank"),
        sa.CheckConstraint("length(trim(location)) > 0", name="assets_location_not_blank"),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"],
            name="fk_assets_created_by_id_users", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
        sa.UniqueConstraint("asset_code", name="uq_assets_asset_code"),
    )
    op.create_index("ix_assets_status_category", "assets", ["status", "category"], unique=False)
    op.create_index("ix_assets_location", "assets", ["location"], unique=False)

    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", work_order_priority, nullable=False),
        sa.Column("status", work_order_status, server_default=sa.text("'open'"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_id", sa.Integer(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(title)) > 0", name="work_orders_title_not_blank"),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"],
            name="fk_work_orders_asset_id_assets", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"],
            name="fk_work_orders_created_by_id_users", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_id"], ["users.id"],
            name="fk_work_orders_assigned_to_id_users", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_orders"),
    )
    op.create_index("ix_work_orders_status_priority", "work_orders", ["status", "priority"], unique=False)
    op.create_index("ix_work_orders_assigned_to_status", "work_orders", ["assigned_to_id", "status"], unique=False)
    op.create_index("ix_work_orders_asset_status", "work_orders", ["asset_id", "status"], unique=False)

    op.create_table(
        "work_order_updates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("update_type", update_type, nullable=False),
        sa.Column("from_status", update_status_from, nullable=True),
        sa.Column("to_status", update_status_to, nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["work_orders.id"],
            name="fk_work_order_updates_work_order_id_work_orders", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"],
            name="fk_work_order_updates_author_id_users", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_order_updates"),
    )
    op.create_index(
        "ix_work_order_updates_work_order_created",
        "work_order_updates",
        ["work_order_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "maintenance_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("performed_by_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("work_performed", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"],
            name="fk_maintenance_records_asset_id_assets", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["work_orders.id"],
            name="fk_maintenance_records_work_order_id_work_orders", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by_id"], ["users.id"],
            name="fk_maintenance_records_performed_by_id_users", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_maintenance_records"),
        sa.UniqueConstraint("work_order_id", name="uq_maintenance_records_work_order_id"),
    )
    op.create_index(
        "ix_maintenance_records_asset_completed_at",
        "maintenance_records",
        ["asset_id", "completed_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_maintenance_records_asset_completed_at", table_name="maintenance_records"
    )
    op.drop_table("maintenance_records")
    op.drop_index(
        "ix_work_order_updates_work_order_created", table_name="work_order_updates"
    )
    op.drop_table("work_order_updates")
    op.drop_index("ix_work_orders_asset_status", table_name="work_orders")
    op.drop_index("ix_work_orders_assigned_to_status", table_name="work_orders")
    op.drop_index("ix_work_orders_status_priority", table_name="work_orders")
    op.drop_table("work_orders")
    op.drop_index("ix_assets_location", table_name="assets")
    op.drop_index("ix_assets_status_category", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_users_role_is_active", table_name="users")
    op.drop_table("users")
