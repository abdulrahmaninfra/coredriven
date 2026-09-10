from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.schema import WorkstationCreate, WorkstationResponse, WorkstationUpdate
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.exceptions import WorkstationNameRequiredError
from src.database.workstations.create import CreateWorkstation
from src.database.workstations.delete import DeleteWorkstation
from src.database.workstations.read import GetWorkstation
from src.database.workstations.update import update_workstation

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
    _require_admin(current_user)
    return CreateWorkstation(
        name=payload.name,
        hourly_rate=payload.hourly_rate,
        is_active=payload.is_active,
    ).create(db)


def _require_admin(current_user: Customer):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage workstations.",
        )


@workstations.put("", response_model=WorkstationResponse)
def update_workstation_endpoint(
    payload: WorkstationUpdate,
    name: str | None = None,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    if not name or not name.strip():
        raise WorkstationNameRequiredError("Workstation name is required.")
    updated = update_workstation(
        db,
        current_name=name.strip(),
        name=payload.name,
        hourly_rate=payload.hourly_rate,
        is_active=payload.is_active,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )
    return updated


@workstations.delete("")
def delete_workstation(
    name: str | None = None,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    if not name or not name.strip():
        raise WorkstationNameRequiredError("Workstation name is required.")
    ended_session_id = (
        DeleteWorkstation(db).delete_by_name(name.strip(), acted_by=current_user)
    )
    return {
        "detail": f"Workstation '{name.strip()}' deleted.",
        "ended_session_id": ended_session_id,
    }
