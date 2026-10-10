"""Database-backed dashboard and reporting queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Asset,
    AssetStatus,
    MaintenanceRecord,
    User,
    UserRole,
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
)


@dataclass(frozen=True)
class ReportFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: WorkOrderStatus | None = None
    priority: WorkOrderPriority | None = None
    asset_id: int | None = None
    assigned_to_id: int | None = None
    performed_by_id: int | None = None
    search: str | None = None
    overdue: bool = False


def _work_order_conditions(
    current_user: User,
    filters: ReportFilters,
    *,
    now: datetime,
) -> list[object]:
    conditions: list[object] = []
    if current_user.role == UserRole.TECHNICIAN:
        conditions.append(WorkOrder.assigned_to_id == current_user.id)
    if filters.date_from is not None:
        conditions.append(WorkOrder.created_at >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(WorkOrder.created_at <= filters.date_to)
    if filters.status is not None:
        conditions.append(WorkOrder.status == filters.status)
    if filters.priority is not None:
        conditions.append(WorkOrder.priority == filters.priority)
    if filters.asset_id is not None:
        conditions.append(WorkOrder.asset_id == filters.asset_id)
    if filters.assigned_to_id is not None:
        conditions.append(WorkOrder.assigned_to_id == filters.assigned_to_id)
    if filters.overdue:
        conditions.extend(
            [
                WorkOrder.due_at.is_not(None),
                WorkOrder.due_at <= now,
                WorkOrder.status.not_in(
                    [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]
                ),
            ]
        )
    if filters.search and filters.search.strip():
        pattern = f"%{filters.search.strip()}%"
        conditions.append(
            or_(
                WorkOrder.title.ilike(pattern),
                WorkOrder.description.ilike(pattern),
                Asset.asset_code.ilike(pattern),
                Asset.name.ilike(pattern),
            )
        )
    return conditions


def _maintenance_conditions(current_user: User, filters: ReportFilters) -> list[object]:
    conditions: list[object] = []
    if current_user.role == UserRole.TECHNICIAN:
        conditions.append(WorkOrder.assigned_to_id == current_user.id)
    if filters.date_from is not None:
        conditions.append(MaintenanceRecord.completed_at >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(MaintenanceRecord.completed_at <= filters.date_to)
    if filters.asset_id is not None:
        conditions.append(MaintenanceRecord.asset_id == filters.asset_id)
    if filters.status is not None:
        conditions.append(WorkOrder.status == filters.status)
    if filters.priority is not None:
        conditions.append(WorkOrder.priority == filters.priority)
    if filters.assigned_to_id is not None:
        conditions.append(WorkOrder.assigned_to_id == filters.assigned_to_id)
    if filters.performed_by_id is not None:
        conditions.append(MaintenanceRecord.performed_by_id == filters.performed_by_id)
    if filters.search and filters.search.strip():
        pattern = f"%{filters.search.strip()}%"
        conditions.append(
            or_(
                MaintenanceRecord.outcome.ilike(pattern),
                MaintenanceRecord.work_performed.ilike(pattern),
                Asset.asset_code.ilike(pattern),
                Asset.name.ilike(pattern),
            )
        )
    return conditions


def _count_work_orders(
    db: Session,
    current_user: User,
    filters: ReportFilters,
    *,
    now: datetime,
) -> int:
    conditions = _work_order_conditions(current_user, filters, now=now)
    return db.scalar(
        select(func.count(WorkOrder.id)).join(Asset).where(*conditions)
    ) or 0


def dashboard_metrics(
    db: Session,
    current_user: User,
    filters: ReportFilters,
    *,
    now: datetime,
) -> dict[str, object]:
    work_order_conditions = _work_order_conditions(current_user, filters, now=now)

    if current_user.role == UserRole.TECHNICIAN:
        asset_counts = db.execute(
            select(Asset.status, func.count(distinct(Asset.id)))
            .join(WorkOrder, WorkOrder.asset_id == Asset.id)
            .where(*work_order_conditions)
            .group_by(Asset.status)
        ).all()
    else:
        asset_counts = db.execute(
            select(Asset.status, func.count(Asset.id)).group_by(Asset.status)
        ).all()
    asset_count_map = {status_value: count for status_value, count in asset_counts}

    total_work_orders = _count_work_orders(db, current_user, filters, now=now)
    outstanding_conditions = work_order_conditions + [
        WorkOrder.status.not_in([WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED])
    ]
    outstanding_work_orders = db.scalar(
        select(func.count(WorkOrder.id)).join(Asset).where(*outstanding_conditions)
    ) or 0
    overdue_work_orders = db.scalar(
        select(func.count(WorkOrder.id))
        .join(Asset)
        .where(
            *work_order_conditions,
            WorkOrder.due_at.is_not(None),
            WorkOrder.due_at <= now,
            WorkOrder.status.not_in([WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]),
        )
    ) or 0
    completed_work_orders = db.scalar(
        select(func.count(WorkOrder.id))
        .join(Asset)
        .where(*work_order_conditions, WorkOrder.status == WorkOrderStatus.COMPLETED)
    ) or 0

    status_rows = db.execute(
        select(WorkOrder.status, func.count(WorkOrder.id))
        .join(Asset)
        .where(*work_order_conditions)
        .group_by(WorkOrder.status)
    ).all()
    status_map = {status_value: count for status_value, count in status_rows}
    priority_rows = db.execute(
        select(WorkOrder.priority, func.count(WorkOrder.id))
        .join(Asset)
        .where(*work_order_conditions)
        .group_by(WorkOrder.priority)
    ).all()
    priority_map = {priority_value: count for priority_value, count in priority_rows}

    maintenance_conditions = _maintenance_conditions(current_user, filters)
    total_maintenance_records = db.scalar(
        select(func.count(MaintenanceRecord.id))
        .join(WorkOrder, WorkOrder.id == MaintenanceRecord.work_order_id)
        .join(Asset, Asset.id == MaintenanceRecord.asset_id)
        .where(*maintenance_conditions)
    ) or 0
    assets_needing_attention = db.scalar(
        select(func.count(distinct(WorkOrder.asset_id)))
        .join(Asset)
        .where(
            *work_order_conditions,
            WorkOrder.status.not_in([WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]),
        )
    ) or 0

    return {
        "as_of": now,
        "total_assets": sum(asset_count_map.values()),
        "active_assets": asset_count_map.get(AssetStatus.ACTIVE, 0),
        "deactivated_assets": asset_count_map.get(AssetStatus.DEACTIVATED, 0),
        "total_work_orders": total_work_orders,
        "outstanding_work_orders": outstanding_work_orders,
        "overdue_work_orders": overdue_work_orders,
        "completed_work_orders": completed_work_orders,
        "status_counts": [
            {"value": item.value, "count": status_map.get(item, 0)}
            for item in WorkOrderStatus
        ],
        "priority_counts": [
            {"value": item.value, "count": priority_map.get(item, 0)}
            for item in WorkOrderPriority
        ],
        "total_maintenance_records": total_maintenance_records,
        "assets_needing_attention": assets_needing_attention,
    }


def work_order_report(
    db: Session,
    current_user: User,
    filters: ReportFilters,
    *,
    skip: int,
    limit: int,
    now: datetime,
) -> tuple[list[WorkOrder], int]:
    conditions = _work_order_conditions(current_user, filters, now=now)
    total = db.scalar(
        select(func.count(WorkOrder.id)).join(Asset).where(*conditions)
    ) or 0
    rows = db.scalars(
        select(WorkOrder)
        .join(Asset)
        .options(
            joinedload(WorkOrder.asset),
            joinedload(WorkOrder.assigned_to),
        )
        .where(*conditions)
        .order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return rows, total


def maintenance_report(
    db: Session,
    current_user: User,
    filters: ReportFilters,
    *,
    skip: int,
    limit: int,
) -> tuple[list[MaintenanceRecord], int]:
    conditions = _maintenance_conditions(current_user, filters)
    base = (
        select(MaintenanceRecord)
        .join(WorkOrder, WorkOrder.id == MaintenanceRecord.work_order_id)
        .join(Asset, Asset.id == MaintenanceRecord.asset_id)
    )
    total = db.scalar(
        select(func.count(MaintenanceRecord.id))
        .join(WorkOrder, WorkOrder.id == MaintenanceRecord.work_order_id)
        .join(Asset, Asset.id == MaintenanceRecord.asset_id)
        .where(*conditions)
    ) or 0
    rows = db.scalars(
        base.options(
            joinedload(MaintenanceRecord.asset),
            joinedload(MaintenanceRecord.performed_by),
        )
        .where(*conditions)
        .order_by(MaintenanceRecord.completed_at.desc(), MaintenanceRecord.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return rows, total

