from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import app.models  # noqa: F401 - registers all models with shared metadata
from app.db.base import Base
from app.models import WorkOrderStatus


EXPECTED_TABLES = {
    "users",
    "assets",
    "work_orders",
    "work_order_updates",
    "maintenance_records",
}


def test_all_phase_three_tables_are_registered() -> None:
    assert EXPECTED_TABLES.issubset(Base.metadata.tables)


def test_foreign_keys_and_relationship_columns_are_defined() -> None:
    assets = Base.metadata.tables["assets"]
    work_orders = Base.metadata.tables["work_orders"]
    updates = Base.metadata.tables["work_order_updates"]
    maintenance = Base.metadata.tables["maintenance_records"]

    assert {str(foreign_key.target_fullname) for foreign_key in assets.c.created_by_id.foreign_keys} == {
        "users.id"
    }
    assert {str(foreign_key.target_fullname) for foreign_key in work_orders.c.asset_id.foreign_keys} == {
        "assets.id"
    }
    assert {str(foreign_key.target_fullname) for foreign_key in updates.c.work_order_id.foreign_keys} == {
        "work_orders.id"
    }
    assert {str(foreign_key.target_fullname) for foreign_key in maintenance.c.performed_by_id.foreign_keys} == {
        "users.id"
    }


def test_unique_and_check_constraints_are_present() -> None:
    users = Base.metadata.tables["users"]
    assets = Base.metadata.tables["assets"]
    maintenance = Base.metadata.tables["maintenance_records"]

    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"email"}
        for constraint in users.constraints
    ) or any(
        index.unique and {column.name for column in index.columns} == {"email"}
        for index in users.indexes
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"asset_code"}
        for constraint in assets.constraints
    ) or any(
        index.unique and {column.name for column in index.columns} == {"asset_code"}
        for index in assets.indexes
    )
    assert any(isinstance(constraint, CheckConstraint) for constraint in users.constraints)
    assert any(isinstance(constraint, CheckConstraint) for constraint in assets.constraints)
    assert maintenance.c.work_order_id.unique is True
    assert {"serial_number", "manufacturer", "model"}.issubset(assets.c.keys())
    assert {"outcome", "work_performed", "completed_at"}.issubset(maintenance.c.keys())


def test_work_order_status_values_match_the_approved_lifecycle() -> None:
    assert {status.value for status in WorkOrderStatus} == {
        "open",
        "assigned",
        "in_progress",
        "on_hold",
        "completed",
        "cancelled",
    }
