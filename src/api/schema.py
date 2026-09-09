from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str
    phone_number: str
    balance: float = 0.0


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    phone_number: str
    balance: float


class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    password: str | None = None
    balance: float | None = None
    is_active: bool | None = None
    # Admin-only: which user to update. Defaults to the caller.
    target_username: str | None = None

class UserSelfUpdate(BaseModel):
    phone_number: str | None = None
    password: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionStart(BaseModel):
    workstation_id: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workstation_id: str
    cost: float | None
    start_time: datetime
    end_time: datetime | None
    status: str


class WorkstationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    hourly_rate: float
    is_active: bool


class WorkstationCreate(BaseModel):
    name: str
    hourly_rate: float = 0.0
    is_active: bool = True
