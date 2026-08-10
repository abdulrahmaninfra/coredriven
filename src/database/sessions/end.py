from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.database.customers.models import Customer
from src.database.exceptions import (
    CustomerNotFoundError,
    SessionNotActiveError,
    SessionNotFoundError,
    WorkstationNotFoundError,
)
from src.database.sessions.models import Sessions
from src.database.workstations.models import Workstation


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def end_session(db: Session, session_id: str):
    session = db.query(Sessions).filter(Sessions.id == session_id).first()
    if not session:
        raise SessionNotFoundError("Session not found")
    if session.status != "active":
        raise SessionNotActiveError("Session is not active")

    customer = db.query(Customer).filter(Customer.id == session.user_id).first()
    if not customer:
        raise CustomerNotFoundError("Customer not found")

    workstation = db.query(Workstation).filter(Workstation.id == session.workstation_id).first()
    if not workstation:
        raise WorkstationNotFoundError("Workstation not found")

    end_time = datetime.now(UTC)
    elapsed_hours = (end_time - _to_utc(session.start_time)).total_seconds() / 3600
    actual_cost = elapsed_hours * workstation.hourly_rate
    actual_cost = min(actual_cost, customer.balance)

    customer.balance -= actual_cost
    session.status = "ended"
    session.end_time = end_time
    session.cost = actual_cost
    workstation.status = "available"

    db.commit()
    db.refresh(session)
    return session
