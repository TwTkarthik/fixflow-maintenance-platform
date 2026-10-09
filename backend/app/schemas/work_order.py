"""Request and response schemas for work-order workflows."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import UpdateType, UserRole, WorkOrderPriority, WorkOrderStatus


def _required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value cannot be blank.")
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_text(value)


def _timezone_aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Datetime values must include a timezone.")
    return value


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    priority: WorkOrderPriority
    due_at: datetime | None = None

    _validate_title = field_validator("title")(_required_text)
    _validate_description = field_validator("description")(_required_text)
    _validate_due_at = field_validator("due_at")(_timezone_aware)


class WorkOrderUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    priority: WorkOrderPriority | None = None
    due_at: datetime | None = None

    _validate_title = field_validator("title")(_optional_text)
    _validate_description = field_validator("description")(_optional_text)
    _validate_due_at = field_validator("due_at")(_timezone_aware)


class AssignWorkOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technician_id: int = Field(gt=0)


class ChangeWorkOrderStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    status: WorkOrderStatus
    note: str | None = Field(default=None, max_length=5000)
    completion_summary: str | None = Field(default=None, max_length=5000)
    work_performed: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_names(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "status" not in normalized and "new_status" in normalized:
            normalized["status"] = normalized.pop("new_status")
        if "completion_summary" not in normalized and "outcome" in normalized:
            normalized["completion_summary"] = normalized.pop("outcome")
        return normalized

    _validate_note = field_validator("note")(_optional_text)
    _validate_completion_summary = field_validator("completion_summary")(_optional_text)
    _validate_work_performed = field_validator("work_performed")(_optional_text)


class RepairNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=5000)

    _validate_note = field_validator("note")(_required_text)


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole


class AssetSummary(BaseModel):
    id: int
    asset_code: str
    name: str


class WorkOrderResponse(BaseModel):
    id: int
    asset_id: int
    asset: AssetSummary
    title: str
    description: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    created_by_id: int
    created_by: UserSummary
    assigned_to_id: int | None
    assigned_to: UserSummary | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    skip: int
    limit: int


class WorkOrderUpdateResponse(BaseModel):
    id: int
    work_order_id: int
    author_id: int
    update_type: UpdateType
    from_status: WorkOrderStatus | None
    to_status: WorkOrderStatus | None
    note: str | None
    author: UserSummary
    created_at: datetime


class MaintenanceRecordResponse(BaseModel):
    id: int
    asset_id: int
    work_order_id: int
    performed_by_id: int
    performed_by: UserSummary
    outcome: str
    work_performed: str
    completed_at: datetime
    created_at: datetime

