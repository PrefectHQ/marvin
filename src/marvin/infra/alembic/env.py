import asyncio

import marvin
from alembic import context
from marvin.infra.database import METADATA, get_dialect
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.

# May 9th 2023: Commented out because it was causing a race condition
#               with the Prefect logger's attempt to configure itself.

# if config.config_file_name is not None:
#     fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = METADATA

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = marvin.settings.database_connection_url.get_secret_value()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Only use batch statements by default on sqlite
        #
        # The SQLite database presents a challenge to migration
        # tools in that it has almost no support for the ALTER statement
        # which relational schema migrations rely upon.
        # Migration tools are instead expected to produce copies of SQLite tables
        # that correspond to the new structure, transfer the data from the existing
        # table to the new one, then drop the old table.
        #
        # see https://alembic.sqlalchemy.org/en/latest/batch.html#batch-migrations
        render_as_batch=get_dialect() == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = create_async_engine(
        marvin.settings.database_connection_url.get_secret_value(),
        echo=marvin.settings.database_echo,
        poolclass=pool.NullPool,
    )

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
