"""Asset tracking for Slackbot - tracking data lineage."""

from datetime import datetime

from prefect.assets import Asset, AssetProperties, add_asset_metadata, materialize
from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelMessage, SystemPromptPart
from raggy.documents import Document
from raggy.vectorstores.tpuf import TurboPuffer

from marvin import cast_async
from slackbot.settings import settings
from slackbot.slack import get_channel_name
from slackbot.types import UserContext


class ThreadSummary(BaseModel):
    title: str
    summary: str
    key_topics: list[str]
    participant_count: int


def slackbot_asset(user_context: UserContext) -> Asset:
    """The slackbot deployment itself as an asset."""
    bot_id = user_context["bot_id"]
    workspace_name = user_context["workspace_name"]
    return Asset(
        key=f"slack://{workspace_name}/bot/{bot_id}",
        properties=AssetProperties(
            name=f"🤖 @ {workspace_name}",
            description=f"Marvin slackbot deployment in workspace {workspace_name}",
            owners=["slackbot"],
        ),
    )


async def slack_thread_asset(user_context: UserContext) -> Asset:
    channel_id = user_context["channel_id"]
    thread_ts = user_context["thread_ts"]
    workspace_name = user_context["workspace_name"]

    # Get the human-readable channel name
    channel_name = await get_channel_name(channel_id)

    return Asset(
        key=f"slack://{workspace_name}/channel/{channel_id}/thread/{thread_ts}",
        properties=AssetProperties(
            name=f"🧵 @ {channel_name}/{thread_ts}",
            description=f"Slack thread in #{channel_name}",
            owners=["slackbot"],
            url=f"https://{workspace_name}.slack.com/archives/{channel_id}/p{thread_ts}",
        ),
    )


def thread_summary_asset(
    user_context: UserContext,
    title: str | None = None,
) -> Asset:
    thread_ts = user_context["thread_ts"]
    channel_id = user_context["channel_id"]
    workspace_name = user_context["workspace_name"]
    bot_id = user_context["bot_id"]
    display_name = title or f"Thread {thread_ts}"
    return Asset(
        key=f"slack://{workspace_name}/bot/{bot_id}/summary/{channel_id}/{thread_ts}",
        properties=AssetProperties(
            name=display_name,
            description=f"AI summary of thread {thread_ts} in #{channel_id}",
            owners=["slackbot"],
        ),
    )


def user_facts_asset(user_context: UserContext) -> Asset:
    user_id = user_context["user_id"]
    workspace_name = user_context["workspace_name"]
    bot_id = user_context["bot_id"]
    return Asset(
        key=f"slack://{workspace_name}/bot/{bot_id}/facts/{user_id}",
        properties=AssetProperties(
            name=f"User Facts {user_id}",
            description=f"Facts learned about user {user_id} by bot {bot_id}",
            owners=["slackbot"],
        ),
    )


async def store_user_facts(ctx: RunContext[UserContext], facts: list[str]) -> str:
    """Store facts extracted from a Slack thread using context for namespacing."""

    with TurboPuffer(
        namespace=f"{settings.user_facts_namespace_prefix}{ctx.deps['user_id']}"
    ) as tpuf:
        tpuf.upsert(documents=[Document(text=fact) for fact in facts])

    user_facts = user_facts_asset(ctx.deps)

    slack_thread = await slack_thread_asset(ctx.deps)
    slackbot = slackbot_asset(ctx.deps)

    @materialize(user_facts, asset_deps=[slack_thread, slackbot])
    async def materialize_user_facts():
        add_asset_metadata(
            user_facts,
            {
                "user_id": ctx.deps["user_id"],
                "fact_count": len(facts),
                "timestamp": datetime.now().isoformat(),
                "namespace": f"{settings.user_facts_namespace_prefix}{ctx.deps['user_id']}",
                "thread_ts": ctx.deps["thread_ts"],
                "workspace_name": ctx.deps["workspace_name"],
                "channel_id": ctx.deps["channel_id"],
                "bot_id": ctx.deps["bot_id"],
                "facts": facts,
            },
        )
        return f"Stored {len(facts)} facts about user {ctx.deps['user_id']} from thread {ctx.deps['thread_ts']}"

    return await materialize_user_facts()


async def summarize_thread(
    user_context: UserContext, conversation: list[ModelMessage]
) -> ThreadSummary:
    """Extract structured summary from a Slack thread using context for namespacing."""

    conversation_parts: list[str] = []
    for message in conversation:
        for part in message.parts:
            if isinstance(part, SystemPromptPart):
                continue
            if hasattr(part, "content"):
                conversation_parts.append(str(part.content))

    conversation_text = "\n\n".join(conversation_parts)

    thread_summary = await cast_async(
        conversation_text,
        target=ThreadSummary,
        instructions="Summarize this slack thread - give a concise but descriptive title.",
    )

    slack_thread = await slack_thread_asset(user_context)
    slackbot = slackbot_asset(user_context)
    summary_asset = thread_summary_asset(
        user_context,
        thread_summary.title,
    )

    @materialize(summary_asset, asset_deps=[slack_thread, slackbot])
    async def materialize_thread_summary():
        add_asset_metadata(
            summary_asset,
            {
                "title": thread_summary.title,
                "summary": thread_summary.summary,
                "thread_ts": user_context["thread_ts"],
                "message_count": len(conversation),
                "workspace_name": user_context["workspace_name"],
                "channel_id": user_context["channel_id"],
                "bot_id": user_context["bot_id"],
                "key_topics": thread_summary.key_topics,
                "participant_count": thread_summary.participant_count,
                "timestamp": datetime.now().isoformat(),
            },
        )
        return thread_summary

    return await materialize_thread_summary()
