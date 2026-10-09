"""Equipment/assets maintained by FixFlow."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AssetStatus


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("length(trim(asset_code)) > 0", name="assets_asset_code_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="assets_name_not_blank"),
        CheckConstraint("length(trim(category)) > 0", name="assets_category_not_blank"),
        CheckConstraint("length(trim(location)) > 0", name="assets_location_not_blank"),
        Index("ix_assets_status_category", "status", "category"),
        Index("ix_assets_location", "location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(160))
    manufacturer: Mapped[str | None] = mapped_column(String(160))
    model: Mapped[str | None] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AssetStatus] = mapped_column(
        SqlEnum(
            AssetStatus,
            name="asset_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=AssetStatus.ACTIVE.value,
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_assets_created_by_id_users", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    created_by: Mapped[User] = relationship(
        back_populates="created_assets", foreign_keys=[created_by_id]
    )
    work_orders: Mapped[list[WorkOrder]] = relationship(
        back_populates="asset", foreign_keys="WorkOrder.asset_id"
    )
    maintenance_records: Mapped[list[MaintenanceRecord]] = relationship(
        back_populates="asset", foreign_keys="MaintenanceRecord.asset_id"
    )
