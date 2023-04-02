import asyncio
import inspect
import io
import logging
import warnings
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import AsyncGenerator, Callable, Literal

import alembic
import sqlmodel
from sqlalchemy.dialects.postgresql import JSONB as postgres_JSONB
from sqlalchemy.dialects.sqlite import JSON as sqlite_JSON
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

import marvin
from marvin import get_logger

logger = get_logger(__name__)

METADATA = sqlmodel.SQLModel.metadata

engine_kwargs = {}
# sqlite doesn't support pool configuration
if marvin.settings.database_connection_url.get_secret_value().startswith("postgresql"):
    engine_kwargs.update(
        pool_size=50,
        max_overflow=20,
    )

engine = create_async_engine(
    marvin.settings.database_connection_url.get_secret_value(),
    echo=marvin.settings.database_echo,
    **engine_kwargs,
)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_dialect() -> Literal["postgresql", "sqlite"]:
    return engine.dialect.name


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    return async_session_maker()


@asynccontextmanager
async def session_context(begin_transaction: bool = False):
    """
    Provides a SQLAlchemy session and a context manager for opening/closing
    the underlying connection.

    Args:
        begin_transaction: if True, the context manager will begin a SQL transaction.
            Exiting the context manager will COMMIT or ROLLBACK any changes.
    """
    async with await get_session() as session:
        if begin_transaction:
            async with session.begin():
                yield session
        else:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def provide_session(begin_transaction: bool = False) -> Callable:
    """
    Decorator that provides a database interface to a function.

    The decorated function _must_ have a kwarg that is annotated as `AsyncSession`.
    """
    if isinstance(begin_transaction, Callable):
        raise TypeError("provide_session() must be called when decorating a function.")

    def wrapper(fn: Callable) -> Callable:
        SESSION_KWARG = None
        sig = inspect.signature(fn)
        for name, param in sig.parameters.items():
            if param.annotation is AsyncSession:
                SESSION_KWARG = name
                break
        if SESSION_KWARG is None:
            raise TypeError("No `AsyncSession` kwarg found in function signature.")

        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            try:
                arguments = sig.bind_partial(*args, **kwargs).arguments

            # typeerror would indicate an illegal argument was passed;
            # we'll let the function reraise for clarity
            except TypeError:
                arguments = {}

            if SESSION_KWARG not in arguments or arguments[SESSION_KWARG] is None:
                async with session_context(
                    begin_transaction=begin_transaction
                ) as session:
                    kwargs[SESSION_KWARG] = session
                    return await fn(*args, **kwargs)
            return await fn(*args, **kwargs)

        return async_wrapper

    return wrapper


if get_dialect() == "sqlite":
    JSONType = sqlite_JSON
else:
    JSONType = postgres_JSONB


async def destroy_db(confirm: bool = False):
    if not confirm:
        raise ValueError("You must confirm that you want to destroy the database.")

    async with session_context(begin_transaction=True) as session:
        for table in reversed(METADATA.sorted_tables):
            if get_dialect() == "postgresql":
                await session.execute(f'DROP TABLE IF EXISTS "{table.name}" CASCADE;')
            else:
                await session.execute(f'DROP TABLE IF EXISTS "{table.name}";')
            marvin.get_logger("db").debug_style(
                f"Table {table.name!r} dropped.", "white on red"
            )
        marvin.get_logger("db").info_style("Database destroyed!", "white on red")


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(METADATA.create_all)
        marvin.get_logger("db").info_style("Database created!", "green")


async def reset_db(confirm: bool = False):
    await destroy_db(confirm=confirm)
    await create_db()


def create_sqlite_db_if_doesnt_exist():
    async def _create_sqlite_db_if_doesnt_exist():
        def has_table(conn):
            import sqlalchemy as _sa

            inspector = _sa.inspect(conn)
            return inspector.has_table("bot_config")

        if get_dialect() == "sqlite":
            async with engine.connect() as conn:
                if not await conn.run_sync(has_table):
                    await create_db()

    asyncio.run(_create_sqlite_db_if_doesnt_exist())


def _alembic_cfg(stdout=None):
    from alembic.config import Config

    alembic_dir = Path(__file__).parent
    if not alembic_dir.joinpath("alembic.ini").exists():
        raise ValueError(f"Couldn't find alembic.ini at {alembic_dir}/alembic.ini")

    kwargs = {}
    if stdout is not None:
        kwargs["stdout"] = stdout
    alembic_cfg = Config(alembic_dir / "alembic.ini", **kwargs)

    return alembic_cfg


def alembic_upgrade(revision: str = "head", dry_run: bool = False):
    """
    Run alembic upgrades on Prefect REST API database

    Args:
        revision: The revision passed to `alembic downgrade`. Defaults to
        'head', upgrading all revisions.
        dry_run: Show what migrations would be made without applying them. Will
        emit sql statements to stdout.
    """
    # lazy import for performance
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), revision, sql=dry_run)


def alembic_downgrade(revision: str = "base", dry_run: bool = False):
    """
    Run alembic downgrades on Prefect REST API database

    Args:
        revision: The revision passed to `alembic downgrade`. Defaults to
        'base', downgrading all revisions.
        dry_run: Show what migrations would be made without applying them. Will
        emit sql statements to stdout.
    """
    # lazy import for performance
    import alembic.command

    alembic.command.downgrade(_alembic_cfg(), revision, sql=dry_run)


def alembic_revision(message: str = None, autogenerate: bool = False, **kwargs):
    """
    Create a new revision file for the database.

    Args:
        message: string message to apply to the revision.
        autogenerate: whether or not to autogenerate the script from the database.
    """
    # lazy import for performance
    import alembic.command

    alembic.command.revision(
        _alembic_cfg(), message=message, autogenerate=autogenerate, **kwargs
    )


async def check_alembic_version():
    # get current alembic version as scalar
    output_buffer = io.StringIO()
    alembic_cfg = _alembic_cfg(stdout=output_buffer)

    # disable alembic logging
    alembic_logger = logging.getLogger("alembic.runtime.migration")
    alembic_logger.disabled = True

    # get current database version
    alembic.command.current(alembic_cfg)
    current = output_buffer.getvalue().strip()

    # if there is no database version, automatically attempt to upgrade
    if not current:
        try:
            marvin.get_logger("database").debug(
                "No database version found; attempting automatic upgrade..."
            )
            alembic.command.upgrade(alembic_cfg, "head")
        except Exception as exc:
            warnings.warn(
                (
                    "The Marvin database appears to be empty and automatic upgrade"
                    " failed. Some features may be broken. Please try to run `marvin"
                    f" database upgrade` manually. Error: {repr(exc)}"
                ),
                UserWarning,
            )
        return

    # get the head version
    output_buffer.seek(0)
    output_buffer.truncate(0)
    alembic.command.heads(alembic_cfg)
    head = output_buffer.getvalue().strip()
    alembic_logger.disabled = False

    if current != head:
        warnings.warn(
            (
                f"Database migrations are not up to date (current version is {current};"
                f" head is {head}). This is expected after upgrading Marvin to a new"
                " version, but some features may be broken until the database is"
                " upgraded. Marvin does not do this automatically; please run `marvin"
                " database upgrade` yourself."
            ),
            UserWarning,
        )
