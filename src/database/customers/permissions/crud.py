from __future__ import annotations

from sqlalchemy.orm import Session

from src.database.customers.permissions.models import AdminPermission

FLAG_FIELDS = (
    "can_manage_admins",
    "can_manage_users",
    "can_manage_workstations",
    "can_manage_billing",
    "read_only_billing",
)


def get_for_customer(db: Session, customer_id: str) -> AdminPermission | None:
    return (
        db.query(AdminPermission)
        .filter(AdminPermission.customer_id == customer_id)
        .first()
    )


def ensure_for_customer(db: Session, customer_id: str) -> AdminPermission:
    row = get_for_customer(db, customer_id)
    if row is None:
        row = AdminPermission(customer_id=customer_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def set_flags(db: Session, customer_id: str, **flags: bool) -> AdminPermission:
    row = ensure_for_customer(db, customer_id)
    updated = False
    for field in FLAG_FIELDS:
        if field in flags and flags[field] is not None:
            setattr(row, field, bool(flags[field]))
            updated = True
    if updated:
        db.commit()
        db.refresh(row)
    return row


def delete_for_customer(db: Session, customer_id: str) -> bool:
    row = get_for_customer(db, customer_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
