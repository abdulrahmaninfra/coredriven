from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    phone_number: str
    balance: float


class UserResponse(BaseModel):
    username: str
    phone_number: str
    balance: float
