import uuid
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from src.database.sessions.models import Sessions
from src.database.customers.models import Customer
from src.database.workstations.models import Workstation

def start_session(db: Session, user_id: str, workstation_id: str):
    customer = db.query(Customer).filter(Customer.id == user_id).first()
    if not customer:
        raise ValueError("User not found")
    customer_balance = customer.balance
    if customer.balance <= 0:
        raise ValueError("Insufficient balance")
    if not workstation_id:
        raise ValueError("Workstation ID is required")
    workstation = db.query(Workstation).filter(Workstation.id == workstation_id).first()
    if not workstation:
        raise ValueError("Workstation not found")
    workstation_hourly_rate = workstation.hourly_rate
    if workstation_hourly_rate <= 0:
        raise ValueError("Invalid workstation hourly rate")
    
    available_minutes = (customer_balance / workstation_hourly_rate) * 60
    end_time = datetime.now() + timedelta(minutes=available_minutes)

    session = Sessions(
        id=str(uuid.uuid4()),
        user_id=user_id,
        workstation_id=workstation_id,
        end_time=end_time,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
        