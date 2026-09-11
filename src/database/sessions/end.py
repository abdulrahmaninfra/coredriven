from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.core.permissions import can_manage_sessions
from src.database.customers.models import Customer
from src.database.exceptions import (
    CustomerNotFoundError,
    NotYourSessionError,
    SessionNotActiveError,
    SessionNotFoundError,
    WorkstationNotFoundError,
)
from src.database.sessions.models import Sessions
from src.database.workstations.models import Workstation


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def end_session(db: Session, session_id: str, acted_by: Customer | None = None):
    session = db.query(Sessions).filter(Sessions.id == session_id).first()
    if not session:
        raise SessionNotFoundError("Session not found")
    if session.status != "active":
        raise SessionNotActiveError("Session is not active")
    if (
        acted_by is not None
        and session.user_id != acted_by.id
        and not can_manage_sessions(acted_by)
    ):
        raise NotYourSessionError("You are not authorized to end this session.")

    customer = db.query(Customer).filter(Customer.id == session.user_id).first()
    if not customer:
        raise CustomerNotFoundError("Customer not found")

    workstation = db.query(Workstation).filter(Workstation.id == session.workstation_id).first()
    if not workstation:
        raise WorkstationNotFoundError("Workstation not found")

    end_time = datetime.now(UTC)
    elapsed_hours = (end_time - _to_utc(session.start_time)).total_seconds() / 3600

    hourly_rate = float(workstation.hourly_rate)
    balance = float(customer.balance)
    actual_cost = round(max(0.0, min(elapsed_hours * hourly_rate, balance)), 2)

    customer.balance = round(balance - actual_cost, 2)
    session.status = "ended"
    session.end_time = end_time
    session.cost = actual_cost
    workstation.status = "available"

    db.commit()
    db.refresh(session)
    return session
