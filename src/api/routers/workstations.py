from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.schema import WorkstationCreate, WorkstationResponse
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.workstations.create import CreateWorkstation
from src.database.workstations.read import GetWorkstation

workstations = APIRouter(prefix="/workstations", tags=["Workstations"])


@workstations.get("", response_model=list[WorkstationResponse])
def list_workstations(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    return GetWorkstation(db).get_all()


@workstations.post(
    "", response_model=WorkstationResponse, status_code=status.HTTP_201_CREATED
)
def create_workstation(
    payload: WorkstationCreate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create workstations.",
        )
    return CreateWorkstation(
        name=payload.name,
        hourly_rate=payload.hourly_rate,
        is_active=payload.is_active,
    ).create(db)
