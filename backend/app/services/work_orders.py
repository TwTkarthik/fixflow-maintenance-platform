"""Transactional work-order business rules."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    Asset,
    AssetStatus,
    MaintenanceRecord,
    UpdateType,
    User,
    UserRole,
    WorkOrder,
    WorkOrderStatus,
    WorkOrderUpdate,
)
from app.schemas.work_order import (
    AssignWorkOrderRequest,
    ChangeWorkOrderStatusRequest,
    RepairNoteRequest,
    WorkOrderCreate,
    WorkOrderUpdateRequest,
)


ALLOWED_TRANSITIONS: dict[WorkOrderStatus, frozenset[WorkOrderStatus]] = {
    WorkOrderStatus.OPEN: frozenset({WorkOrderStatus.ASSIGNED, WorkOrderStatus.CANCELLED}),
    WorkOrderStatus.ASSIGNED: frozenset(
        {
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.ON_HOLD,
            WorkOrderStatus.OPEN,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.IN_PROGRESS: frozenset(
        {
            WorkOrderStatus.ON_HOLD,
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.CANCELLED,
        }
    ),
    WorkOrderStatus.ON_HOLD: frozenset(
        {WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED}
    ),
    WorkOrderStatus.COMPLETED: frozenset(),
    WorkOrderStatus.CANCELLED: frozenset(),
}

TECHNICIAN_TRANSITIONS: frozenset[tuple[WorkOrderStatus, WorkOrderStatus]] = frozenset(
    {
        (WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS),
        (WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.ON_HOLD),
        (WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.COMPLETED),
        (WorkOrderStatus.ON_HOLD, WorkOrderStatus.IN_PROGRESS),
    }
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found.")


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def _bad_transition(current: WorkOrderStatus, requested: WorkOrderStatus) -> HTTPException:
    return _conflict(f"Cannot transition a {current.value} work order to {requested.value}.")


def ensure_visible(work_order: WorkOrder, current_user: User) -> WorkOrder:
    """Enforce technician scope without revealing another user's work order."""

    if current_user.role == UserRole.TECHNICIAN and work_order.assigned_to_id != current_user.id:
        raise _not_found()
    return work_order


def get_visible_work_order(db: Session, work_order_id: int, current_user: User) -> WorkOrder:
    work_order = db.get(WorkOrder, work_order_id)
    if work_order is None:
        raise _not_found()
    return ensure_visible(work_order, current_user)


def _append_update(
    db: Session,
    *,
    work_order_id: int,
    author_id: int,
    update_type: UpdateType,
    from_status: WorkOrderStatus | None = None,
    to_status: WorkOrderStatus | None = None,
    note: str | None = None,
) -> WorkOrderUpdate:
    update = WorkOrderUpdate(
        work_order_id=work_order_id,
        author_id=author_id,
        update_type=update_type,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    db.add(update)
    return update


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_maintenance_records_work_order_id" in str(error.orig).lower():
            raise _conflict("This work order already has a maintenance record.") from error
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def create_work_order(
    db: Session, payload: WorkOrderCreate, current_user: User
) -> WorkOrder:
    asset = db.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    if asset.status != AssetStatus.ACTIVE:
        raise _conflict("Deactivated assets cannot receive new work orders.")

    work_order = WorkOrder(
        asset_id=asset.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=WorkOrderStatus.OPEN,
        created_by_id=current_user.id,
        due_at=payload.due_at,
    )
    db.add(work_order)
    db.flush()
    _append_update(
        db,
        work_order_id=work_order.id,
        author_id=current_user.id,
        update_type=UpdateType.STATUS_CHANGE,
        to_status=WorkOrderStatus.OPEN,
        note="Work order created.",
    )
    _commit(db)
    return work_order


def update_work_order(
    db: Session,
    work_order: WorkOrder,
    payload: WorkOrderUpdateRequest,
) -> WorkOrder:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one editable field is required.")
    if "description" in changes and changes["description"] is None:
        raise HTTPException(status_code=422, detail="Description cannot be cleared.")
    for field_name, value in changes.items():
        setattr(work_order, field_name, value)
    _commit(db)
    return work_order


def assign_work_order(
    db: Session,
    work_order_id: int,
    payload: AssignWorkOrderRequest,
    current_user: User,
) -> WorkOrder:
    work_order = db.scalar(
        select(WorkOrder).where(WorkOrder.id == work_order_id).with_for_update()
    )
    if work_order is None:
        raise _not_found()
    if work_order.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
        raise _conflict("Terminal work orders cannot be assigned.")

    technician = db.get(User, payload.technician_id)
    if technician is None or technician.role != UserRole.TECHNICIAN or not technician.is_active:
        raise HTTPException(
            status_code=422,
            detail="Assignment requires an active technician account.",
        )
    if work_order.assigned_to_id == technician.id:
        return work_order

    previous_assignee = work_order.assigned_to_id
    previous_status = work_order.status
    if previous_status == WorkOrderStatus.OPEN:
        work_order.status = WorkOrderStatus.ASSIGNED
    work_order.assigned_to_id = technician.id
    work_order.assigned_to = technician
    note = f"Assigned to {technician.full_name} (user {technician.id})."
    if previous_assignee is not None:
        note = f"Reassigned to {technician.full_name} (user {technician.id})."
    _append_update(
        db,
        work_order_id=work_order.id,
        author_id=current_user.id,
        update_type=UpdateType.ASSIGNMENT,
        from_status=previous_status,
        to_status=work_order.status,
        note=note,
    )
    _commit(db)
    return work_order


def transition_work_order(
    db: Session,
    work_order_id: int,
    payload: ChangeWorkOrderStatusRequest,
    current_user: User,
) -> WorkOrder:
    work_order = db.scalar(
        select(WorkOrder).where(WorkOrder.id == work_order_id).with_for_update()
    )
    if work_order is None:
        raise _not_found()
    ensure_visible(work_order, current_user)

    current_status = work_order.status
    requested_status = payload.status
    if requested_status not in ALLOWED_TRANSITIONS[current_status]:
        raise _bad_transition(current_status, requested_status)
    if current_user.role == UserRole.TECHNICIAN:
        if (current_status, requested_status) not in TECHNICIAN_TRANSITIONS:
            raise HTTPException(
                status_code=403,
                detail="Technicians cannot perform this work-order transition.",
            )
    if requested_status in {
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.COMPLETED,
    } and work_order.assigned_to_id is None:
        raise _conflict("This transition requires an assigned technician.")

    completion_summary = payload.completion_summary or payload.note
    if requested_status == WorkOrderStatus.COMPLETED and not completion_summary:
        raise HTTPException(
            status_code=422,
            detail="A completion summary is required when completing a work order.",
        )

    now = datetime.now(UTC)
    if requested_status == WorkOrderStatus.OPEN:
        work_order.assigned_to_id = None
        work_order.assigned_to = None
    work_order.status = requested_status
    if requested_status == WorkOrderStatus.COMPLETED:
        work_order.completed_at = now
        maintenance = MaintenanceRecord(
            asset_id=work_order.asset_id,
            work_order_id=work_order.id,
            performed_by_id=work_order.assigned_to_id,
            outcome=completion_summary,
            work_performed=payload.work_performed or completion_summary,
            completed_at=now,
        )
        db.add(maintenance)

    history_note = payload.note or completion_summary
    _append_update(
        db,
        work_order_id=work_order.id,
        author_id=current_user.id,
        update_type=UpdateType.STATUS_CHANGE,
        from_status=current_status,
        to_status=requested_status,
        note=history_note,
    )
    _commit(db)
    return work_order


def add_work_order_note(
    db: Session,
    work_order_id: int,
    payload: RepairNoteRequest,
    current_user: User,
) -> WorkOrderUpdate:
    work_order = get_visible_work_order(db, work_order_id, current_user)
    if work_order.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
        raise _conflict("Terminal work orders cannot receive new notes.")
    update = _append_update(
        db,
        work_order_id=work_order.id,
        author_id=current_user.id,
        update_type=UpdateType.NOTE,
        note=payload.note,
    )
    _commit(db)
    return update

