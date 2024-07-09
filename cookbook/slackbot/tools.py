import asyncio
import contextlib
from contextvars import ContextVar
from typing import Optional

from marvin.utilities.slack import get_thread_messages, post_slack_message
from raggy.vectorstores.tpuf import multi_query_tpuf
from tenacity import retry, stop_after_attempt

USER_CONTEXT = ContextVar("user_context", default=None)


@contextlib.contextmanager
def user_context(user_id: str, channel_id: str, thread_ts: str):
    token = USER_CONTEXT.set(
        {"user_id": user_id, "channel_id": channel_id, "thread_ts": thread_ts}
    )
    try:
        yield
    finally:
        USER_CONTEXT.reset(token)


def get_current_user_context():
    return USER_CONTEXT.get()


async def get_current_message_text(channel: str, ts: str) -> str:
    messages = await get_thread_messages(channel, ts)
    for message in messages:
        if message["ts"] == ts:
            return message["text"]
    raise ValueError("Message not found")


@retry(stop=stop_after_attempt(2))
async def get_more_info_from_user(prompt: str, timeout: int = 60) -> Optional[str]:
    if not (context := get_current_user_context()):
        raise ValueError("User context not set")

    await post_slack_message(
        message=prompt, channel_id=context["channel_id"], thread_ts=context["thread_ts"]
    )

    initial_content = await get_current_message_text(
        context["channel_id"], context["thread_ts"]
    )

    async def check_for_edit():
        while True:
            current_content = await get_current_message_text(
                context["channel_id"], context["thread_ts"]
            )
            if current_content != initial_content:
                return current_content
            await asyncio.sleep(1)

    try:
        return await asyncio.wait_for(check_for_edit(), timeout=timeout)
    except asyncio.TimeoutError:
        await post_slack_message(
            message="No response received. Please try again if you need assistance.",
            channel_id=context["channel_id"],
            thread_ts=context["thread_ts"],
        )
        return None


async def search_knowledgebase(
    queries: list[str], namespace: str = "marvin-slackbot"
) -> str:
    return await multi_query_tpuf(queries=queries, namespace=namespace)
