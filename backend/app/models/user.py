"""User account model used by future authentication and authorization phases."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(full_name)) > 0", name="users_full_name_not_blank"),
        CheckConstraint("length(trim(email)) > 0", name="users_email_not_blank"),
        Index("ix_users_role_is_active", "role", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    created_assets: Mapped[list[Asset]] = relationship(
        back_populates="created_by", foreign_keys="Asset.created_by_id"
    )
    created_work_orders: Mapped[list[WorkOrder]] = relationship(
        back_populates="created_by", foreign_keys="WorkOrder.created_by_id"
    )
    assigned_work_orders: Mapped[list[WorkOrder]] = relationship(
        back_populates="assigned_to", foreign_keys="WorkOrder.assigned_to_id"
    )
    work_order_updates: Mapped[list[WorkOrderUpdate]] = relationship(
        back_populates="author", foreign_keys="WorkOrderUpdate.author_id"
    )
    maintenance_records: Mapped[list[MaintenanceRecord]] = relationship(
        back_populates="performed_by", foreign_keys="MaintenanceRecord.performed_by_id"
    )
