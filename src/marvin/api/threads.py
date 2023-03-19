import sqlalchemy as sa
from fastapi import Body, Depends, HTTPException, Path, Query, status

from marvin.api.dependencies import fastapi_session
from marvin.infra.db import AsyncSession, provide_session
from marvin.models.ids import ThreadID
from marvin.models.threads import (
    Message,
    MessageCreate,
    Thread,
    ThreadCreate,
    ThreadUpdate,
    UserMessageCreate,
)
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
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return thread


@router.get("/{id}")
@provide_session()
async def get_thread(
    thread_id: ThreadID = Path(..., alias="id"),
    session: AsyncSession = Depends(fastapi_session),
) -> Thread | None:
    result = await session.execute(
        sa.select(Thread).where(Thread.id == thread_id).limit(1)
    )
    thread = result.scalar()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return thread


@provide_session()
async def get_or_create_thread_by_lookup_key(
    lookup_key: str,
    session: AsyncSession,
) -> Thread:
    try:
        thread = await get_thread_by_lookup_key(lookup_key=lookup_key, session=session)
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            thread = await create_thread(
                thread=ThreadCreate(lookup_key=lookup_key), session=session
            )
        else:
            raise e
    return thread


@provide_session()
async def create_message(
    thread_id: ThreadID = Path(..., alias="id"),
    message: MessageCreate = Body(...),
    session: AsyncSession = Depends(fastapi_session),
) -> None:
    session.add(Message(**message.dict(), thread_id=thread_id))
    await session.commit()


@router.post("/{id}", status_code=status.HTTP_201_CREATED)
@provide_session()
async def create_user_message(
    thread_id: ThreadID = Path(..., alias="id"),
    message: UserMessageCreate = Body(...),
    session: AsyncSession = Depends(fastapi_session),
) -> None:
    await create_message(message=message, thread_id=thread_id, session=session)


@router.get("/{id}/messages")
@provide_session()
async def get_messages(
    thread_id: ThreadID = Path(..., alias="id"),
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
    return list(reversed(result.scalars().all()))


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@provide_session()
async def update_thread(
    thread_id: ThreadID = Path(..., alias="id"),
    thread: ThreadUpdate = Body(...),
    session: AsyncSession = Depends(fastapi_session),
):
    await session.execute(
        sa.update(Thread)
        .where(Thread.id == thread_id)
        .values(**thread.dict(exclude_unset=True))
    )
    await session.commit()
