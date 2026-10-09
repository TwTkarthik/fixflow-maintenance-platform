"""Append-only activity and status-history model for work orders."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UpdateType, WorkOrderStatus


class WorkOrderUpdate(Base):
    __tablename__ = "work_order_updates"
    __table_args__ = (Index("ix_work_order_updates_work_order_created", "work_order_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "work_orders.id", name="fk_work_order_updates_work_order_id_work_orders", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_work_order_updates_author_id_users", ondelete="RESTRICT"),
        nullable=False,
    )
    update_type: Mapped[UpdateType] = mapped_column(
        SqlEnum(
            UpdateType,
            name="work_order_update_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    from_status: Mapped[WorkOrderStatus | None] = mapped_column(
        SqlEnum(
            WorkOrderStatus,
            name="work_order_update_from_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    to_status: Mapped[WorkOrderStatus | None] = mapped_column(
        SqlEnum(
            WorkOrderStatus,
            name="work_order_update_to_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    work_order: Mapped[WorkOrder] = relationship(back_populates="updates", foreign_keys=[work_order_id])
    author: Mapped[User] = relationship(back_populates="work_order_updates", foreign_keys=[author_id])
