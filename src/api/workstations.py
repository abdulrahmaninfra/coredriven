from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.schema import WorkstationResponse
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.workstations.read import GetWorkstation

workstations = APIRouter(prefix="/workstations", tags=["Workstations"])


@workstations.get("", response_model=list[WorkstationResponse])
def list_workstations(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    return GetWorkstation(db).get_all()
