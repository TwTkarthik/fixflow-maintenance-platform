"""Response schemas for dashboard and reporting endpoints."""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import WorkOrderPriority, WorkOrderStatus
from app.schemas.work_order import UserSummary


class MetricCount(BaseModel):
    value: str
    count: int


class DashboardResponse(BaseModel):
    as_of: datetime
    total_assets: int
    active_assets: int
    deactivated_assets: int
    total_work_orders: int
    outstanding_work_orders: int
    overdue_work_orders: int
    completed_work_orders: int
    status_counts: list[MetricCount]
    priority_counts: list[MetricCount]
    total_maintenance_records: int
    assets_needing_attention: int


class WorkOrderReportRow(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    created_by_id: int
    assigned_to_id: int | None
    assigned_to: UserSummary | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    is_overdue: bool


class WorkOrderReportResponse(BaseModel):
    items: list[WorkOrderReportRow]
    total: int
    skip: int
    limit: int


class MaintenanceReportRow(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    work_order_id: int
    performed_by_id: int
    performed_by: UserSummary
    outcome: str
    work_performed: str
    completed_at: datetime
    created_at: datetime


class MaintenanceReportResponse(BaseModel):
    items: list[MaintenanceReportRow]
    total: int
    skip: int
    limit: int

