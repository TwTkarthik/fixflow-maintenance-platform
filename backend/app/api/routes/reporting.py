"""Authenticated dashboard and reporting endpoints."""

from datetime import UTC, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import User, WorkOrderPriority, WorkOrderStatus
from app.schemas.reporting import (
    DashboardResponse,
    MaintenanceReportResponse,
    MaintenanceReportRow,
    WorkOrderReportResponse,
    WorkOrderReportRow,
)
from app.schemas.work_order import UserSummary
from app.services.reporting import ReportFilters, dashboard_metrics, maintenance_report, work_order_report


router = APIRouter(prefix="/api", tags=["dashboard", "reports"])
CurrentUser = Annotated[User, Depends(get_current_user)]


def _parse_bound(value: str | None, *, name: str, end: bool) -> datetime | None:
    if value is None or not value.strip():
        return None
    raw = value.strip()
    try:
        if len(raw) == 10:
            parsed_date = datetime.strptime(raw, "%Y-%m-%d").date()
            if end:
                return datetime.combine(parsed_date, time.max, tzinfo=UTC)
            return datetime.combine(parsed_date, time.min, tzinfo=UTC)
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("timezone is required")
        return parsed.astimezone(UTC)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must be a YYYY-MM-DD date or timezone-aware ISO-8601 datetime.",
        ) from error


def _report_filters(
    *,
    date_from: str | None,
    date_to: str | None,
    status: WorkOrderStatus | None = None,
    priority: WorkOrderPriority | None = None,
    asset_id: int | None = None,
    assigned_to_id: int | None = None,
    performed_by_id: int | None = None,
    search: str | None = None,
    overdue: bool = False,
) -> ReportFilters:
    parsed_from = _parse_bound(date_from, name="date_from", end=False)
    parsed_to = _parse_bound(date_to, name="date_to", end=True)
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise HTTPException(status_code=422, detail="date_from must be before date_to.")
    return ReportFilters(
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        priority=priority,
        asset_id=asset_id,
        assigned_to_id=assigned_to_id,
        performed_by_id=performed_by_id,
        search=search,
        overdue=overdue,
    )


def _user_summary(user: User) -> UserSummary:
    return UserSummary(id=user.id, full_name=user.full_name, email=user.email, role=user.role)


def _work_order_row(work_order, *, now: datetime) -> WorkOrderReportRow:
    is_overdue = (
        work_order.due_at is not None
        and work_order.due_at <= now
        and work_order.status not in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}
    )
    return WorkOrderReportRow(
        id=work_order.id,
        asset_id=work_order.asset_id,
        asset_code=work_order.asset.asset_code,
        asset_name=work_order.asset.name,
        title=work_order.title,
        priority=work_order.priority,
        status=work_order.status,
        created_by_id=work_order.created_by_id,
        assigned_to_id=work_order.assigned_to_id,
        assigned_to=_user_summary(work_order.assigned_to) if work_order.assigned_to else None,
        due_at=work_order.due_at,
        created_at=work_order.created_at,
        updated_at=work_order.updated_at,
        completed_at=work_order.completed_at,
        is_overdue=is_overdue,
    )


def _maintenance_row(record) -> MaintenanceReportRow:
    return MaintenanceReportRow(
        id=record.id,
        asset_id=record.asset_id,
        asset_code=record.asset.asset_code,
        asset_name=record.asset.name,
        work_order_id=record.work_order_id,
        performed_by_id=record.performed_by_id,
        performed_by=_user_summary(record.performed_by),
        outcome=record.outcome,
        work_performed=record.work_performed,
        completed_at=record.completed_at,
        created_at=record.created_at,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    date_from: str | None = Query(default=None, max_length=40),
    date_to: str | None = Query(default=None, max_length=40),
) -> DashboardResponse:
    filters = _report_filters(date_from=date_from, date_to=date_to)
    return DashboardResponse.model_validate(
        dashboard_metrics(db, current_user, filters, now=datetime.now(UTC))
    )


@router.get("/reports/work-orders", response_model=WorkOrderReportResponse)
def get_work_order_report(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    date_from: str | None = Query(default=None, max_length=40),
    date_to: str | None = Query(default=None, max_length=40),
    status: WorkOrderStatus | None = None,
    priority: WorkOrderPriority | None = None,
    asset_id: int | None = Query(default=None, gt=0),
    assigned_to_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=200),
    overdue: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> WorkOrderReportResponse:
    filters = _report_filters(
        date_from=date_from,
        date_to=date_to,
        status=status,
        priority=priority,
        asset_id=asset_id,
        assigned_to_id=assigned_to_id,
        search=search,
        overdue=overdue,
    )
    now = datetime.now(UTC)
    rows, total = work_order_report(
        db, current_user, filters, skip=skip, limit=limit, now=now
    )
    return WorkOrderReportResponse(
        items=[_work_order_row(row, now=now) for row in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/reports/maintenance", response_model=MaintenanceReportResponse)
def get_maintenance_report(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    date_from: str | None = Query(default=None, max_length=40),
    date_to: str | None = Query(default=None, max_length=40),
    status: WorkOrderStatus | None = None,
    priority: WorkOrderPriority | None = None,
    asset_id: int | None = Query(default=None, gt=0),
    assigned_to_id: int | None = Query(default=None, gt=0),
    performed_by_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> MaintenanceReportResponse:
    filters = _report_filters(
        date_from=date_from,
        date_to=date_to,
        status=status,
        priority=priority,
        asset_id=asset_id,
        assigned_to_id=assigned_to_id,
        performed_by_id=performed_by_id,
        search=search,
    )
    rows, total = maintenance_report(
        db, current_user, filters, skip=skip, limit=limit
    )
    return MaintenanceReportResponse(
        items=[_maintenance_row(row) for row in rows],
        total=total,
        skip=skip,
        limit=limit,
    )

