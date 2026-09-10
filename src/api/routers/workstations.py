from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.schema import WorkstationCreate, WorkstationResponse, WorkstationUpdate
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.exceptions import WorkstationIdRequiredError
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


@workstations.put(
    "/{workstation_id}",
    response_model=WorkstationResponse,
    summary="Update workstation by ID",
)
def update_workstation_endpoint(
    workstation_id: str,
    payload: WorkstationUpdate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    if not workstation_id or not workstation_id.strip():
        raise WorkstationIdRequiredError("Workstation ID is required.")
    updated = update_workstation(
        db,
        workstation_id=workstation_id.strip(),
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


@workstations.delete("/{workstation_id}", summary="Delete workstation by ID")
def delete_workstation(
    workstation_id: str,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    if not workstation_id or not workstation_id.strip():
        raise WorkstationIdRequiredError("Workstation ID is required.")
    workstation_id = workstation_id.strip()
    ended_session_id = DeleteWorkstation(db).delete_by_id(
        workstation_id, acted_by=current_user
    )
    return {
        "detail": f"Workstation '{workstation_id}' deleted.",
        "ended_session_id": ended_session_id,
    }
