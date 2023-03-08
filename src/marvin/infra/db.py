import inspect
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator, Callable, Literal

import sqlmodel
from sqlalchemy.dialects.postgresql import JSONB as postgres_JSONB
from sqlalchemy.dialects.sqlite import JSON as sqlite_JSON
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

import marvin

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
        for table in reversed(sqlmodel.SQLModel.metadata.sorted_tables):
            if marvin.database.engine.get_dialect() == "postgresql":
                await session.execute(f'DROP TABLE IF EXISTS "{table.name}" CASCADE;')
            else:
                await session.execute(f'DROP TABLE IF EXISTS "{table.name}";')
            marvin.get_logger("db").debug_style(
                f"Table {table.name!r} dropped.", "white on red"
            )
        marvin.get_logger("db").info_style("Database destroyed!", "white on red")


async def create_db():
    async with marvin.database.engine.engine.begin() as conn:
        await conn.run_sync(sqlmodel.SQLModel.metadata.create_all)
        marvin.get_logger("db").info_style("Database created!", "green")


async def reset_db(confirm: bool = False):
    await destroy_db(confirm=confirm)
    await create_db()
