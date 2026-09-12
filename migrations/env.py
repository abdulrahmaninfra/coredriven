"""Alembic environment for CoreDriven.

Wired to the app's own configuration:
- target metadata = the single shared Base from src/database/customers/database.py
- database URL   = the app's _resolve_database_url() (settings.DATABASE_URL,
  falling back to sqlite:///{DATABASE_NAME}) -- same URL the app runs on.

Requires the same env vars as running the app (HOST, PORT, FIRST_SUPERADMIN_*)
or a .env file, because get_settings() validates all of them.
"""

import os
import sys
from logging.config import fileConfig

# Make project-root imports (src.*, main) work regardless of where alembic
# is invoked from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import engine_from_config, pool

from alembic import context

from src.database.customers.database import Base, _resolve_database_url

# Import every model module so each one registers its tables on Base.metadata
# (same imports create_db() performs before create_all).
import src.database.customers.models  # noqa: F401
import src.database.customers.permissions.models  # noqa: F401
import src.database.sessions.models  # noqa: F401
import src.database.transactions.models  # noqa: F401
import src.database.workstations.models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Set the URL from the app's settings (not from alembic.ini) so migrations
# always target the same database the app talks to. '%' must be doubled for
# configparser interpolation.
config.set_main_option("sqlalchemy.url", _resolve_database_url().replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()