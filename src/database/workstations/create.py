import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.exceptions import (
    InvalidWorkstationRateError,
    WorkstationNameRequiredError,
    WorkstationNameTakenError,
)
from src.database.workstations.models import Workstation


class CreateWorkstation:
    def __init__(self, name: str, hourly_rate: float = 0.0, is_active: bool = True):
        self.id = str(uuid.uuid4())
        self.name = name
        self.hourly_rate = hourly_rate
        self.is_active = is_active

    def create(self, db: Session):
        name = (self.name or "").strip()
        if not name:
            raise WorkstationNameRequiredError("Workstation name is required.")
        if float(self.hourly_rate) <= 0:
            raise InvalidWorkstationRateError("Invalid workstation hourly rate.")

        existing = db.query(Workstation).filter(Workstation.name == name).first()
        if existing:
            raise WorkstationNameTakenError(
                f"Workstation name '{name}' is already taken."
            )

        workstation = Workstation(
            id=self.id,
            name=name,
            status="available",
            hourly_rate=round(float(self.hourly_rate), 2),
            is_active=self.is_active,
        )
        db.add(workstation)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise WorkstationNameTakenError(
                f"Workstation name '{name}' is already taken."
            )
        db.refresh(workstation)
        return workstation
