"""Domain values used by the initial database schema."""

from enum import StrEnum


class UserRole(StrEnum):
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    TECHNICIAN = "technician"


class AssetStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class WorkOrderPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkOrderStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UpdateType(StrEnum):
    STATUS_CHANGE = "status_change"
    NOTE = "note"
    ASSIGNMENT = "assignment"
