"""Asset tracking for Slackbot - tracking data lineage."""

from datetime import datetime

from prefect.assets import Asset, AssetProperties, add_asset_metadata, materialize
from raggy.documents import Document
from raggy.vectorstores.tpuf import TurboPuffer

from slackbot.settings import settings

# Asset representing a Slack conversation/thread
CONVERSATION = Asset(
    key="slack://conversation",
    properties=AssetProperties(
        name="Slack Conversation",
        description="Individual Slack thread or conversation",
        owners=["slackbot"],
    ),
)

# Asset representing facts extracted from conversations
USER_FACTS = Asset(
    key="turbopuffer://user-facts",
    properties=AssetProperties(
        name="User Facts",
        description="Facts extracted from user conversations",
        owners=["slackbot"],
    ),
)


@materialize(USER_FACTS, asset_deps=[CONVERSATION])
async def store_user_facts(user_id: str, facts: list[str]) -> str:
    """Store facts extracted from a conversation."""

    # Store facts in vector DB
    with TurboPuffer(
        namespace=f"{settings.user_facts_namespace_prefix}{user_id}"
    ) as tpuf:
        tpuf.upsert(documents=[Document(text=fact) for fact in facts])

    # Track metadata about this extraction
    add_asset_metadata(
        USER_FACTS,
        {
            "user_id": user_id,
            "fact_count": len(facts),
            "timestamp": datetime.now().isoformat(),
            "namespace": f"{settings.user_facts_namespace_prefix}{user_id}",
        },
    )

    return f"Stored {len(facts)} facts about user {user_id}"
