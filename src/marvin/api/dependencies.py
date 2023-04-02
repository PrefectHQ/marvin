from typing import AsyncGenerator

from marvin.infra.database import AsyncSession, session_context


async def fastapi_session() -> AsyncGenerator[AsyncSession, None]:
    """Get session and commit or rollback after request is complete"""
    async with session_context(begin_transaction=False) as session:
        try:
            yield session
            # always commit after we return from the request body
            await session.commit()
        except Exception:
            await session.rollback()
