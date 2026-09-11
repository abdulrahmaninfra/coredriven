import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.database.customers.models import Customer
from src.database.exceptions import (
    InsufficientBalanceError,
    InvalidWorkstationRateError,
    UserAlreadyHasActiveSessionError,
    UserDeactivatedError,
    UserNotFoundError,
    WorkstationDeactivatedError,
    WorkstationIdRequiredError,
    WorkstationNotFoundError,
    WorkstationUnavailableError,
)
from src.database.sessions.models import Sessions
from src.database.workstations.models import Workstation


def start_session(db: Session, user_id: str, workstation_id: str):
    customer = db.query(Customer).filter(Customer.id == user_id).first()
    if not customer:
        raise UserNotFoundError("User not found")
    if not customer.is_active:
        raise UserDeactivatedError("This account has been deactivated")
    if customer.balance <= 0:
        raise InsufficientBalanceError("Insufficient balance")

    if not workstation_id:
        raise WorkstationIdRequiredError("Workstation ID is required")

    workstation = db.query(Workstation).filter(Workstation.id == workstation_id).first()
    if not workstation:
        raise WorkstationNotFoundError("Workstation not found")
    if not workstation.is_active:
        raise WorkstationDeactivatedError("Workstation is deactivated")
    if workstation.status != "available":
        raise WorkstationUnavailableError("Workstation is not available")
    if workstation.hourly_rate <= 0:
        raise InvalidWorkstationRateError("Invalid workstation hourly rate")

    active_session = (
        db.query(Sessions)
        .filter(Sessions.user_id == user_id, Sessions.status == "active")
        .first()
    )
    if active_session:
        raise UserAlreadyHasActiveSessionError("User already has an active session")

    start_time = datetime.now(UTC)
    available_minutes = (
        float(float(customer.balance) / float(workstation.hourly_rate)) * 60
    )
    end_time = start_time + timedelta(minutes=available_minutes)

    session = Sessions(
        id=str(uuid.uuid4()),
        user_id=user_id,
        workstation_id=workstation_id,
        start_time=start_time,
        end_time=end_time,
        status="active",
    )
    db.add(session)
    workstation.status = "occupied"
    db.commit()
    db.refresh(session)
    return session
