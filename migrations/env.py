import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add the parent directory to sys.path so we can import from marvin
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the SQLAlchemy declarative Base from marvin
# This is the Alembic Config object
from alembic.config import Config

from marvin.database import Base
from marvin.settings import settings

config = Config("alembic.ini")

# Convert async URL to sync URL for Alembic
config.set_main_option("sqlalchemy.url", settings.database_url or "")

# Interpret the config file for logging
fileConfig(config.config_file_name, disable_existing_loggers=False)

# Set metadata to use from the database module
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Enable batch operations for SQLite
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with the given connection."""
    # Check if we're using SQLite

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Enable batch operations for SQLite
        render_as_batch=(connection.dialect.name == "sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Get the connection from config attributes if it was provided
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        # If no connection provided, run the async migrations
        asyncio.run(run_async_migrations())
    else:
        # If a connection was provided (e.g., for autogenerate), use it directly
        do_run_migrations(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
