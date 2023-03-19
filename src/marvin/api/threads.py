import sqlalchemy as sa
from fastapi import Depends, HTTPException, Query, status

from marvin.api.dependencies import fastapi_session
from marvin.infra.db import AsyncSession, provide_session
from marvin.models.ids import ThreadID
from marvin.models.threads import Message, Thread, ThreadCreate, ThreadUpdate
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(prefix="/threads", tags=["Threads"])


@router.post("/", status_code=status.HTTP_201_CREATED)
@provide_session()
async def create_thread(
    thread: ThreadCreate, session: AsyncSession = Depends(fastapi_session)
) -> Thread:
    session.add(thread)
    await session.commit()
    return thread


@router.post("/lookup/{lookup_key}")
@provide_session()
async def get_thread_by_lookup_key(
    lookup_key: str,
    session: AsyncSession = Depends(fastapi_session),
) -> Thread | None:
    result = await session.execute(
        sa.select(Thread).where(Thread.lookup_key == lookup_key).limit(1)
    )
    thread = result.scalar()
    return thread


@router.get("/{thread_id}")
@provide_session()
async def get_thread(
    thread_id: ThreadID,
    session: AsyncSession = Depends(fastapi_session),
) -> Thread | None:
    result = await session.execute(
        sa.select(Thread).where(Thread.id == thread_id).limit(1)
    )
    thread = result.scalar()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return thread


@router.get("/{thread_id}/messages")
@provide_session()
async def get_messages(
    thread_id: ThreadID,
    n: int = Query(100, ge=0, le=100),
    session: AsyncSession = Depends(fastapi_session),
) -> list[Message]:
    query = (
        sa.select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.timestamp.desc())
        .limit(n)
    )
    result = await session.execute(query)
    return result.scalars().all()


@router.patch("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
@provide_session()
async def update_thread(
    thread_id: ThreadID,
    thread: ThreadUpdate,
    session: AsyncSession = Depends(fastapi_session),
):
    await session.execute(
        sa.update(Thread)
        .where(Thread.id == thread_id)
        .values(**thread.dict(exclude_unset=True))
    )
    await session.commit()
