import fastapi.params
import sqlalchemy as sa
from fastapi import Body, Depends, HTTPException, Path, Query, status

from marvin.api.dependencies import fastapi_session
from marvin.infra.database import AsyncSession, provide_session
from marvin.models.bots import BotConfig
from marvin.models.ids import ThreadID
from marvin.models.threads import (
    Message,
    MessageCreate,
    MessageRead,
    Thread,
    ThreadCreate,
    ThreadRead,
    ThreadUpdate,
)
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(prefix="/threads", tags=["Threads"])


@router.post("/", status_code=status.HTTP_201_CREATED)
@provide_session()
async def create_thread(
    thread: ThreadCreate, session: AsyncSession = Depends(fastapi_session)
) -> ThreadRead:
    db_thread = Thread(**thread.dict())
    session.add(db_thread)
    try:
        await session.commit()
    # this shouldn't happen unless an internal function is creating a thread
    # with a known ID
    except sa.exc.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT)
    return ThreadRead(**db_thread.dict())


@router.post("/lookup/{lookup_key}")
@provide_session()
async def get_thread_by_lookup_key(
    lookup_key: str,
    session: AsyncSession = Depends(fastapi_session),
) -> ThreadRead:
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
) -> ThreadRead:
    result = await session.execute(
        sa.select(Thread).where(Thread.id == thread_id).limit(1)
    )
    thread = result.scalar()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return thread


@router.get("/")
@provide_session()
async def get_threads_by_bot(
    bot_name: str,
    session: AsyncSession = Depends(fastapi_session),
    limit: int = Query(100, ge=0, le=100),
    offset: int = Query(0, ge=0),
    only_visible: bool = Query(True),
) -> list[ThreadRead]:
    if isinstance(limit, fastapi.params.Query):
        limit = limit.default
    if isinstance(offset, fastapi.params.Query):
        offset = offset.default
    if isinstance(only_visible, fastapi.params.Query):
        only_visible = only_visible.default

    exists_clause = (
        sa.select(Message)
        .join(BotConfig, BotConfig.id == Message.bot_id)
        .where(BotConfig.name == bot_name, Message.thread_id == Thread.id)
    )
    query = (
        sa.select(Thread)
        .where(exists_clause.exists())
        .order_by(Thread.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if only_visible:
        query = query.where(Thread.is_visible.is_(True))
    result = await session.execute(query)
    return result.scalars().all()


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


# @router.post("/{id}", status_code=status.HTTP_201_CREATED)
# @provide_session()
# async def create_user_message(
#     thread_id: ThreadID = Path(..., alias="id"),
#     message: UserMessageCreate = Body(...),
#     session: AsyncSession = Depends(fastapi_session),
# ) -> None:
#     await create_message(message=message, thread_id=thread_id, session=session)


@router.get("/{id}/messages")
@provide_session()
async def get_messages(
    thread_id: ThreadID = Path(..., alias="id"),
    limit: int = Query(100, ge=0, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(fastapi_session),
) -> list[MessageRead]:
    if isinstance(limit, fastapi.params.Query):
        limit = limit.default
    if isinstance(offset, fastapi.params.Query):
        offset = offset.default

    query = (
        sa.select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .offset(offset)
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
