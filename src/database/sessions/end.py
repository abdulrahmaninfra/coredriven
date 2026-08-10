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
    
    customer = db.query(Customer).filter(Customer.id == session.user_id).first()
    if not customer:
        raise ValueError("Customer not found")
    workstation = db.query(Workstation).filter(Workstation.id == session.workstation_id).first()
    if not workstation:
        raise ValueError("Workstation not found")
    
    actual_cost = (datetime.now() - session.start_time).total_seconds() / 3600 * workstation.hourly_rate
    customer_balance = customer.balance
    customer_balance -= actual_cost
    customer.balance = customer_balance

    session.status = "ended"
    session.end_time = datetime.now()
    session.cost = actual_cost
    workstation.status = "available"
    
    db.commit()
    db.refresh(session)
    return session