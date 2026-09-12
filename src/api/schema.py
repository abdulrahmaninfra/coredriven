from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str
    password: str
    phone_number: str
    balance: float = 0.0


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    phone_number: str
    balance: float
    is_admin: bool = False
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    password: str | None = None
    balance: float | None = None
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    phone_number: str | None = None
    password: str | None = None


class UserCharge(BaseModel):
    target_username: str | None = None
    amount: float


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


class WorkstationUpdate(BaseModel):
    name: str | None = None
    hourly_rate: float | None = None
    is_active: bool | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: float
    balance_after: float
    note: str = "null"
    created_at: datetime


class TransactionMove(BaseModel):
    target_username: str
    amount: float = Field(gt=0)
    note: str = "null"


class TransactionResult(BaseModel):
    transaction: TransactionResponse
    username: str
    new_balance: float


class TransactionListItem(BaseModel):
    id: str
    username: str
    amount: float
    balance_after: float
    note: str = "null"
    created_at: datetime


class AdminPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    can_manage_admins: bool = False
    can_manage_users: bool = False
    can_manage_workstations: bool = False
    can_manage_billing: bool = False
    read_only_billing: bool = False


class AdminPermissionUpdate(BaseModel):
    can_manage_admins: bool | None = None
    can_manage_users: bool | None = None
    can_manage_workstations: bool | None = None
    can_manage_billing: bool | None = None
    read_only_billing: bool | None = None


class UserAdminUpdate(BaseModel):
    is_admin: bool | None = None
    is_superadmin: bool | None = None
    permissions: AdminPermissionUpdate | None = None


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    is_admin: bool = False
    is_superadmin: bool = False
    permissions: AdminPermissionResponse | None = None
