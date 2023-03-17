import sqlalchemy as sa
from fastapi import Body, HTTPException, Query, status

import marvin
from marvin.infra.db import AsyncSession, provide_session
from marvin.models.digests import Digest
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
    session: AsyncSession = None,
) -> Topic:
    session.add(topic)
    await session.commit()
    return topic


@router.get("/{topic}")
@provide_session()
async def get_topic(
    topic: str,
    session: AsyncSession = None,
) -> Topic:
    result = await session.execute(sa.select(Topic).where(Topic.name == topic).limit(1))
    topic = result.scalar()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@provide_session()
async def get_topic_by_id(
    topic_id: TopicID,
    session: AsyncSession = None,
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
    session: AsyncSession = None,
    limit: int = Query(25, gte=0, lte=100),
    after: str = Query(None),
) -> list[Topic]:
    query = (
        sa.select(Topic)
        .where(Topic.name > after if after else True)
        .order_by(Topic.name)
        .limit(limit)
    )
    result = await session.execute(query)
    topics = result.scalars().all()
    return topics


@router.delete(
    "/{topic}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@provide_session()
async def delete_topic(
    topic: str,
    session: AsyncSession = None,
):
    chroma = marvin.infra.chroma.Chroma()
    await chroma.delete(where=dict(topic=topic))
    db_topic = await get_topic(topic, session=session)
    await delete_topic_by_id(topic_id=db_topic.id, session=session)


@provide_session()
async def delete_topic_by_id(
    topic_id: TopicID,
    session: AsyncSession = None,
):
    await marvin.services.chroma.delete_vectors(
        filter={"topic_id": topic_id}, namespace=marvin.settings.pinecone_namespace
    )
    await session.execute(sa.delete(Topic).where(Topic.id == topic_id))
    await session.commit()


@router.put(
    "/{topic}",
    status_code=status.HTTP_200_OK,
)
async def update_topic(
    topic: str,
    digest: Digest,
):
    chroma = marvin.infra.chroma.Chroma(collection_name=topic)

    chroma.add(**digest.dict())
