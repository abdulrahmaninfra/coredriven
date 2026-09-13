from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# All money values are Decimal (exact base-10) capped at 2 decimal places,
# matching the Numeric(10, 2) columns in the database. In JSON they are
# serialized back to plain numbers (not strings) so the API contract is
# identical to the previous float-based schemas.
Money = Annotated[
    Decimal,
    Field(max_digits=10, decimal_places=2),
    PlainSerializer(float, return_type=float),
]

# Money that must be strictly positive (e.g. transaction amounts).
PositiveMoney = Annotated[
    Decimal,
    Field(max_digits=10, decimal_places=2, gt=0),
    PlainSerializer(float, return_type=float),
]

ZERO = Decimal("0.00")


class UserCreate(BaseModel):
    username: str
    password: str
    phone_number: str
    balance: Money = ZERO


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    phone_number: str
    balance: Money
    is_admin: bool = False
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    password: str | None = None
    balance: Money | None = None
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    phone_number: str | None = None
    password: str | None = None


class UserCharge(BaseModel):
    target_username: str | None = None
    amount: Money


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
    cost: Money | None
    start_time: datetime
    end_time: datetime | None
    status: str


class WorkstationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    hourly_rate: Money
    is_active: bool


class WorkstationCreate(BaseModel):
    name: str
    hourly_rate: Money = ZERO
    is_active: bool = True


class WorkstationUpdate(BaseModel):
    name: str | None = None
    hourly_rate: Money | None = None
    is_active: bool | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: Money
    balance_after: Money
    note: str = "null"
    created_at: datetime


class TransactionMove(BaseModel):
    target_username: str
    amount: PositiveMoney
    note: str = "null"


class TransactionResult(BaseModel):
    transaction: TransactionResponse
    username: str
    new_balance: Money


class TransactionListItem(BaseModel):
    id: str
    username: str
    amount: Money
    balance_after: Money
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