from datetime import datetime
from sqlalchemy.orm import Session as s
from src.database.customers.models import Customer
from src.database.sessions.models import Sessions
from src.database.workstations.models import Workstation

def end_session(db: s, session_id: str):
    session = db.query(Sessions).filter(Sessions.id == session_id).first()
    if not session:
        raise ValueError("Session not found")
    if session.status != "active":
        raise ValueError("Session is not active")
    
    session.status = "ended"
    session.end_time = datetime.now()

    customer = db.query(Customer).filter(Customer.id == session.user_id).first()
    workstation = db.query(Workstation).filter(Workstation.id == session.workstation_id).first()
    workstation_hourly_rate = workstation.hourly_rate
    customer_balance = customer.balance
    customer_balance -= (session.end_time - session.start_time).total_seconds() / 3600 * workstation_hourly_rate
    customer.balance = customer_balance

    db.commit()
    db.refresh(session)
    return session