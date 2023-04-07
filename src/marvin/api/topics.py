import fastapi.params
import sqlalchemy as sa
from fastapi import Body, Depends, HTTPException, Path, Query, status

import marvin
from marvin.api.dependencies import fastapi_session
from marvin.infra.database import AsyncSession, provide_session
from marvin.models.topics import Topic, TopicID
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(prefix="/topics", tags=["Topics"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
@provide_session()
async def create_topic(
    topic: Topic = Body(),
    session: AsyncSession = Depends(fastapi_session),
) -> Topic:
    session.add(topic)
    await session.commit()
    return topic


@router.get("/{name}")
@provide_session()
async def get_topic(
    topic_name: str = Path(..., alias="name"),
    session: AsyncSession = Depends(fastapi_session),
) -> Topic:
    result = await session.execute(
        sa.select(Topic).where(Topic.name == topic_name).limit(1)
    )
    topic = result.scalar()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@provide_session()
async def get_topic_by_id(
    topic_id: TopicID,
    session: AsyncSession = Depends(fastapi_session),
) -> Topic:
    result = await session.execute(
        sa.select(Topic).where(Topic.id == topic_id).limit(1)
    )
    topic = result.scalar()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.get("/")
@provide_session()
async def get_topics(
    session: AsyncSession = Depends(fastapi_session),
    limit: int = Query(25, gte=0, lte=100),
    offset: int = Query(0, gte=0),
    after: str = Query(None),
) -> list[Topic]:
    if isinstance(limit, fastapi.params.Query):
        limit = limit.default
    if isinstance(offset, fastapi.params.Query):
        offset = offset.default

    query = (
        sa.select(Topic)
        .where(Topic.name > after if after else True)
        .order_by(Topic.name)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    topics = result.scalars().all()
    return topics


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@provide_session()
async def delete_topic(
    topic_name: str = Path(..., alias="name"),
    session: AsyncSession = Depends(fastapi_session),
):
    async with marvin.infra.chroma.Chroma() as chroma:
        await chroma.delete(where=dict(topic=topic_name))
    db_topic = await get_topic(topic_name, session=session)
    await delete_topic_by_id(topic_id=db_topic.id, session=session)


@provide_session()
async def delete_topic_by_id(
    topic_id: TopicID,
    session: AsyncSession = Depends(fastapi_session),
):
    await session.execute(sa.delete(Topic).where(Topic.id == topic_id))
    await session.commit()
