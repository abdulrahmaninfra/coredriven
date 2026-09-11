from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.customers.database import Base

if TYPE_CHECKING:
    from src.database.customers.models import Customer


class AdminPermission(Base):
    __tablename__ = "admin_permissions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String, ForeignKey("customers.id"), unique=True, nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    can_manage_admins: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    can_manage_users: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    can_manage_workstations: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    can_manage_billing: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    read_only_billing: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="admin_permission")
