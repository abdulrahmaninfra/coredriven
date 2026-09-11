from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.database.exceptions import NotAdminError

if TYPE_CHECKING:
    from src.database.customers.models import Customer

MANAGE_FLAGS = (
    "can_manage_admins",
    "can_manage_users",
    "can_manage_workstations",
    "can_manage_billing",
)

SESSION_FLAGS = (
    "can_manage_users",
    "can_manage_workstations",
    "can_manage_billing",
)


def is_superadmin(user: Customer) -> bool:
    return bool(getattr(user, "is_superadmin", False))


def has_permission(user: Customer, flag: str) -> bool:
    """Superadmins bypass every check; sub-admins need `is_admin` + the flag."""
    if is_superadmin(user):
        return True
    if not getattr(user, "is_admin", False):
        return False
    perm: Any = getattr(user, "admin_permission", None)
    return bool(perm is not None and getattr(perm, flag, False))


def require_permission(user: Customer, flag: str, action: str) -> None:
    if not has_permission(user, flag):
        raise NotAdminError(f"Requires '{flag}' permission to {action}.")


def can_manage_sessions(user: Customer) -> bool:
    """Any operational flag (users / workstations / billing) covers sessions."""
    if is_superadmin(user):
        return True
    return any(has_permission(user, flag) for flag in SESSION_FLAGS)


def require_session_management(user: Customer, action: str) -> None:
    if not can_manage_sessions(user):
        raise NotAdminError(
            f"Requires one of {list(SESSION_FLAGS)} to {action}."
        )


def can_read_billing(user: Customer) -> bool:
    if has_permission(user, "can_manage_billing"):
        return True
    if not getattr(user, "is_admin", False):
        return False
    perm: Any = getattr(user, "admin_permission", None)
    return bool(perm is not None and perm.read_only_billing)


def require_billing_read(user: Customer, action: str) -> None:
    if not can_read_billing(user):
        raise NotAdminError(f"Requires billing access to {action}.")


def require_billing_write(user: Customer, action: str) -> None:
    require_permission(user, "can_manage_billing", action)
