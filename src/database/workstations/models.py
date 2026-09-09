
from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.customers.database import Base


class Workstation(Base):
    __tablename__ = "workstations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="available")
    hourly_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
