from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.database.customers.database import Base

class Sessions(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey="customers.id")
    workstation_id: Mapped[str] = mapped_column(String(50), ForeignKey="workstations.id")
    start_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)