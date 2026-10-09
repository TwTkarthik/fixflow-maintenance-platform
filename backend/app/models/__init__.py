"""Import all ORM models so metadata and Alembic see every table."""

from app.models.asset import Asset
from app.models.enums import (
    AssetStatus,
    UpdateType,
    UserRole,
    WorkOrderPriority,
    WorkOrderStatus,
)
from app.models.maintenance_record import MaintenanceRecord
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_update import WorkOrderUpdate

__all__ = [
    "Asset",
    "AssetStatus",
    "MaintenanceRecord",
    "UpdateType",
    "User",
    "UserRole",
    "WorkOrder",
    "WorkOrderPriority",
    "WorkOrderStatus",
    "WorkOrderUpdate",
]
