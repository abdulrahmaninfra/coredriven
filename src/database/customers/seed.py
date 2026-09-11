from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.database.customers.create import CreateNewUser
from src.database.customers.models import Customer
from src.database.customers.permissions.crud import set_flags
from src.database.customers.read import GetUser


def ensure_first_superadmin(db: Session):
    """Create or promote the bootstrap superadmin from settings.

    Idempotent: if a superadmin already exists, or the configured user is
    already a superadmin, nothing changes.
    """
    settings = get_settings()
    username = settings.FIRST_SUPERADMIN_EMAIL
    existing_super = db.query(Customer).filter_by(is_superadmin=True).first()
    if existing_super is not None:
        return existing_super

    user = GetUser(db).get_user_by_username(username)
    if user is None:
        user = CreateNewUser(
            username=username,
            password=settings.FIRST_SUPERADMIN_PASSWORD,
            phone_number="0000000000",
            balance=0.0,
        ).create_user(db)

    user.is_admin = True
    user.is_superadmin = True
    db.commit()
    set_flags(
        db,
        user.id,
        can_manage_admins=True,
        can_manage_users=True,
        can_manage_workstations=True,
        can_manage_billing=True,
        read_only_billing=False,
    )
    db.refresh(user)
    return user
