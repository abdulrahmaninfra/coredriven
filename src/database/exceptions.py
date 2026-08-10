"""Custom domain exceptions raised by the database layer."""


class AppError(Exception):
    """Base class for all application domain errors."""


class UserNotFoundError(AppError):
    pass


class UserDeactivatedError(AppError):
    pass


class InsufficientBalanceError(AppError):
    pass


class UserAlreadyHasActiveSessionError(AppError):
    pass


class WorkstationIdRequiredError(AppError):
    pass


class WorkstationNotFoundError(AppError):
    pass


class WorkstationDeactivatedError(AppError):
    pass


class WorkstationUnavailableError(AppError):
    pass


class InvalidWorkstationRateError(AppError):
    pass


class SessionNotFoundError(AppError):
    pass


class SessionNotActiveError(AppError):
    pass


class CustomerNotFoundError(AppError):
    pass
