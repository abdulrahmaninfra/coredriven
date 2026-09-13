from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.database.exceptions import (
    AppError,
    CustomerNotFoundError,
    InsufficientBalanceError,
    InvalidWorkstationRateError,
    NotAdminError,
    NotYourSessionError,
    SessionNotActiveError,
    SessionNotFoundError,
    UserAlreadyHasActiveSessionError,
    UserDeactivatedError,
    UserNotFoundError,
    WorkstationDeactivatedError,
    WorkstationIdRequiredError,
    WorkstationNameRequiredError,
    WorkstationNameTakenError,
    WorkstationNotFoundError,
    WorkstationUnavailableError,
    BalanceOverflowError,
)

ERROR_STATUS_MAP: dict[type[AppError], int] = {
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    SessionNotFoundError: status.HTTP_404_NOT_FOUND,
    CustomerNotFoundError: status.HTTP_404_NOT_FOUND,
    WorkstationNotFoundError: status.HTTP_404_NOT_FOUND,
    UserDeactivatedError: status.HTTP_403_FORBIDDEN,
    NotYourSessionError: status.HTTP_403_FORBIDDEN,
    InsufficientBalanceError: status.HTTP_400_BAD_REQUEST,
    WorkstationIdRequiredError: status.HTTP_400_BAD_REQUEST,
    WorkstationNameRequiredError: status.HTTP_400_BAD_REQUEST,
    InvalidWorkstationRateError: status.HTTP_400_BAD_REQUEST,
    UserAlreadyHasActiveSessionError: status.HTTP_409_CONFLICT,
    WorkstationNameTakenError: status.HTTP_409_CONFLICT,
    WorkstationUnavailableError: status.HTTP_409_CONFLICT,
    WorkstationDeactivatedError: status.HTTP_409_CONFLICT,
    SessionNotActiveError: status.HTTP_409_CONFLICT,
    NotAdminError: status.HTTP_403_FORBIDDEN,
    BalanceOverflowError: status.HTTP_400_BAD_REQUEST,
}


async def app_error_handler(request: Request, exc: AppError):
    status_code = ERROR_STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})
