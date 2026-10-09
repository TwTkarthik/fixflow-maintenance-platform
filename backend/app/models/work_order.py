"""Repair and maintenance request model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import WorkOrderPriority, WorkOrderStatus


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="work_orders_title_not_blank"),
        Index("ix_work_orders_status_priority", "status", "priority"),
        Index("ix_work_orders_assigned_to_status", "assigned_to_id", "status"),
        Index("ix_work_orders_asset_status", "asset_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", name="fk_work_orders_asset_id_assets", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[WorkOrderPriority] = mapped_column(
        SqlEnum(
            WorkOrderPriority,
            name="work_order_priority",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        SqlEnum(
            WorkOrderStatus,
            name="work_order_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=WorkOrderStatus.OPEN.value,
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_work_orders_created_by_id_users", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_work_orders_assigned_to_id_users", ondelete="SET NULL")
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    asset: Mapped[Asset] = relationship(back_populates="work_orders", foreign_keys=[asset_id])
    created_by: Mapped[User] = relationship(
        back_populates="created_work_orders", foreign_keys=[created_by_id]
    )
    assigned_to: Mapped[User | None] = relationship(
        back_populates="assigned_work_orders", foreign_keys=[assigned_to_id]
    )
    updates: Mapped[list[WorkOrderUpdate]] = relationship(
        back_populates="work_order", foreign_keys="WorkOrderUpdate.work_order_id"
    )
    maintenance_record: Mapped[MaintenanceRecord | None] = relationship(
        back_populates="work_order", foreign_keys="MaintenanceRecord.work_order_id", uselist=False
    )
