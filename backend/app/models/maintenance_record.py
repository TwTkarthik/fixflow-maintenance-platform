"""Completed maintenance history model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    __table_args__ = (Index("ix_maintenance_records_asset_completed_at", "asset_id", "completed_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", name="fk_maintenance_records_asset_id_assets", ondelete="RESTRICT"),
        nullable=False,
    )
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "work_orders.id", name="fk_maintenance_records_work_order_id_work_orders", ondelete="RESTRICT"
        ),
        unique=True,
        nullable=False,
    )
    performed_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", name="fk_maintenance_records_performed_by_id_users", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    work_performed: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    asset: Mapped[Asset] = relationship(back_populates="maintenance_records", foreign_keys=[asset_id])
    work_order: Mapped[WorkOrder] = relationship(
        back_populates="maintenance_record", foreign_keys=[work_order_id]
    )
    performed_by: Mapped[User] = relationship(
        back_populates="maintenance_records", foreign_keys=[performed_by_id]
    )
