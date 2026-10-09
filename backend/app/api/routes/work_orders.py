"""Authenticated work-order, history, and status workflow endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models import (
    Asset,
    MaintenanceRecord,
    User,
    UserRole,
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderUpdate,
)
from app.schemas.work_order import (
    AssetSummary,
    AssignWorkOrderRequest,
    ChangeWorkOrderStatusRequest,
    MaintenanceRecordResponse,
    RepairNoteRequest,
    UserSummary,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderUpdateRequest,
    WorkOrderUpdateResponse,
    WorkOrderCreate,
)
from app.services.work_orders import (
    add_work_order_note,
    assign_work_order,
    create_work_order,
    get_visible_work_order,
    transition_work_order,
    update_work_order,
)


router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])
ManagerOrAdministrator = Annotated[
    User,
    Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.MANAGER)),
]


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )


def _work_order_response(work_order: WorkOrder) -> WorkOrderResponse:
    return WorkOrderResponse(
        id=work_order.id,
        asset_id=work_order.asset_id,
        asset=AssetSummary(
            id=work_order.asset.id,
            asset_code=work_order.asset.asset_code,
            name=work_order.asset.name,
        ),
        title=work_order.title,
        description=work_order.description,
        priority=work_order.priority,
        status=work_order.status,
        created_by_id=work_order.created_by_id,
        created_by=_user_summary(work_order.created_by),
        assigned_to_id=work_order.assigned_to_id,
        assigned_to=_user_summary(work_order.assigned_to) if work_order.assigned_to else None,
        due_at=work_order.due_at,
        created_at=work_order.created_at,
        updated_at=work_order.updated_at,
        completed_at=work_order.completed_at,
    )


def _load_work_order(db: Session, work_order_id: int, current_user: User) -> WorkOrder:
    work_order = db.scalar(
        select(WorkOrder)
        .options(
            joinedload(WorkOrder.asset),
            joinedload(WorkOrder.created_by),
            joinedload(WorkOrder.assigned_to),
        )
        .where(WorkOrder.id == work_order_id)
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found.")
    get_visible_work_order(db, work_order.id, current_user)
    return work_order


def _update_response(update: WorkOrderUpdate) -> WorkOrderUpdateResponse:
    return WorkOrderUpdateResponse(
        id=update.id,
        work_order_id=update.work_order_id,
        author_id=update.author_id,
        update_type=update.update_type,
        from_status=update.from_status,
        to_status=update.to_status,
        note=update.note,
        author=_user_summary(update.author),
        created_at=update.created_at,
    )


def _maintenance_response(record: MaintenanceRecord) -> MaintenanceRecordResponse:
    return MaintenanceRecordResponse(
        id=record.id,
        asset_id=record.asset_id,
        work_order_id=record.work_order_id,
        performed_by_id=record.performed_by_id,
        performed_by=_user_summary(record.performed_by),
        outcome=record.outcome,
        work_performed=record.work_performed,
        completed_at=record.completed_at,
        created_at=record.created_at,
    )


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=200),
    work_order_status: WorkOrderStatus | None = Query(default=None, alias="status"),
    priority: WorkOrderPriority | None = None,
    asset_id: int | None = Query(default=None, gt=0),
    assigned_to_id: int | None = Query(default=None, gt=0),
    creator_id: int | None = Query(default=None, gt=0),
    overdue: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> WorkOrderListResponse:
    filters = []
    if current_user.role == UserRole.TECHNICIAN:
        filters.append(WorkOrder.assigned_to_id == current_user.id)
    if work_order_status is not None:
        filters.append(WorkOrder.status == work_order_status)
    if priority is not None:
        filters.append(WorkOrder.priority == priority)
    if asset_id is not None:
        filters.append(WorkOrder.asset_id == asset_id)
    if assigned_to_id is not None:
        filters.append(WorkOrder.assigned_to_id == assigned_to_id)
    if creator_id is not None:
        filters.append(WorkOrder.created_by_id == creator_id)
    if overdue:
        filters.extend(
            [
                WorkOrder.due_at.is_not(None),
                WorkOrder.due_at < datetime.now(UTC),
                WorkOrder.status.not_in(
                    [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]
                ),
            ]
        )
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                WorkOrder.title.ilike(pattern),
                WorkOrder.description.ilike(pattern),
                Asset.asset_code.ilike(pattern),
                Asset.name.ilike(pattern),
            )
        )

    where_clause = tuple(filters)
    base = select(WorkOrder).join(Asset)
    total = db.scalar(select(func.count(WorkOrder.id)).join(Asset).where(*where_clause)) or 0
    work_orders = db.scalars(
        base.options(
            joinedload(WorkOrder.asset),
            joinedload(WorkOrder.created_by),
            joinedload(WorkOrder.assigned_to),
        )
        .where(*where_clause)
        .order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return WorkOrderListResponse(
        items=[_work_order_response(work_order) for work_order in work_orders],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
def create_work_order_endpoint(
    payload: WorkOrderCreate,
    current_user: ManagerOrAdministrator,
    db: Session = Depends(get_db),
) -> WorkOrderResponse:
    work_order = create_work_order(db, payload, current_user)
    return _work_order_response(_load_work_order(db, work_order.id, current_user))


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrderResponse:
    return _work_order_response(_load_work_order(db, work_order_id, current_user))


@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
def update_work_order_endpoint(
    work_order_id: int,
    payload: WorkOrderUpdateRequest,
    current_user: ManagerOrAdministrator,
    db: Session = Depends(get_db),
) -> WorkOrderResponse:
    work_order = get_visible_work_order(db, work_order_id, current_user)
    update_work_order(db, work_order, payload)
    return _work_order_response(_load_work_order(db, work_order_id, current_user))


@router.post("/{work_order_id}/assign", response_model=WorkOrderResponse)
def assign_work_order_endpoint(
    work_order_id: int,
    payload: AssignWorkOrderRequest,
    current_user: ManagerOrAdministrator,
    db: Session = Depends(get_db),
) -> WorkOrderResponse:
    assign_work_order(db, work_order_id, payload, current_user)
    return _work_order_response(_load_work_order(db, work_order_id, current_user))


@router.post("/{work_order_id}/status", response_model=WorkOrderResponse)
def change_work_order_status(
    work_order_id: int,
    payload: ChangeWorkOrderStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrderResponse:
    transition_work_order(db, work_order_id, payload, current_user)
    return _work_order_response(_load_work_order(db, work_order_id, current_user))


@router.post("/{work_order_id}/notes", response_model=WorkOrderUpdateResponse, status_code=201)
def add_work_order_note_endpoint(
    work_order_id: int,
    payload: RepairNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkOrderUpdateResponse:
    update = add_work_order_note(db, work_order_id, payload, current_user)
    db.refresh(update)
    update.author = current_user
    return _update_response(update)


@router.get("/{work_order_id}/history", response_model=list[WorkOrderUpdateResponse])
def get_work_order_history(
    work_order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkOrderUpdateResponse]:
    work_order = get_visible_work_order(db, work_order_id, current_user)
    updates = db.scalars(
        select(WorkOrderUpdate)
        .options(joinedload(WorkOrderUpdate.author))
        .where(WorkOrderUpdate.work_order_id == work_order.id)
        .order_by(WorkOrderUpdate.created_at, WorkOrderUpdate.id)
    ).all()
    return [_update_response(update) for update in updates]


@router.get("/{work_order_id}/maintenance", response_model=MaintenanceRecordResponse)
def get_work_order_maintenance(
    work_order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRecordResponse:
    work_order = get_visible_work_order(db, work_order_id, current_user)
    record = db.scalar(
        select(MaintenanceRecord)
        .options(joinedload(MaintenanceRecord.performed_by))
        .where(MaintenanceRecord.work_order_id == work_order.id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found.")
    return _maintenance_response(record)

