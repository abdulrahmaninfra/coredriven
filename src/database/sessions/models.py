from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.customers.database import Base


class Sessions(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("customers.id"), index=True)
    workstation_id: Mapped[str] = mapped_column(String, ForeignKey("workstations.id"), index=True)
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    __table_args__ = (
        Index(
            "uq_sessions_active_user",
            "user_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "uq_sessions_active_workstation",
            "workstation_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )
