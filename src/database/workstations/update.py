from sqlalchemy.orm import Session

from src.database.exceptions import (
    InvalidWorkstationRateError,
    WorkstationNameRequiredError,
    WorkstationNameTakenError,
    WorkstationNotFoundError,
)
from src.database.workstations.read import GetWorkstation


def update_workstation(
    db: Session,
    current_name: str,
    name: str | None = None,
    hourly_rate: float | None = None,
    is_active: bool | None = None,
):

    workstation = GetWorkstation(db).get_by_name(current_name)
    if workstation is None:
        raise WorkstationNotFoundError(f"Workstation '{current_name}' not found.")

    values = {}

    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise WorkstationNameRequiredError("Workstation name is required.")
        if cleaned != workstation.name:
            if GetWorkstation(db).get_by_name(cleaned) is not None:
                raise WorkstationNameTakenError(
                    f"Workstation name '{cleaned}' is already taken."
                )
            values["name"] = cleaned

    if hourly_rate is not None:
        if float(hourly_rate) <= 0:
            raise InvalidWorkstationRateError("Invalid workstation hourly rate.")
        values["hourly_rate"] = round(float(hourly_rate), 2)

    if is_active is not None:
        values["is_active"] = is_active

    if not values:
        return None

    for field, value in values.items():
        setattr(workstation, field, value)
    db.commit()
    db.refresh(workstation)
    return workstation
