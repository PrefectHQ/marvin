"""Module for Slack-related utilities."""
import os
import re
from typing import List, Optional, Union

import httpx
from pydantic import BaseModel, field_validator

import marvin


class EventBlockElement(BaseModel):
    type: str
    text: Optional[str] = None
    user_id: Optional[str] = None


class EventBlockElementGroup(BaseModel):
    type: str
    elements: List[EventBlockElement]


class EventBlock(BaseModel):
    type: str
    block_id: str
    elements: List[Union[EventBlockElement, EventBlockElementGroup]]


class SlackEvent(BaseModel):
    client_msg_id: Optional[str] = None
    type: str
    text: str
    user: str
    ts: str
    team: str
    channel: str
    event_ts: str
    thread_ts: Optional[str] = None
    parent_user_id: Optional[str] = None
    blocks: Optional[List[EventBlock]] = None


class EventAuthorization(BaseModel):
    enterprise_id: Optional[str] = None
    team_id: str
    user_id: str
    is_bot: bool
    is_enterprise_install: bool


class SlackPayload(BaseModel):
    token: str
    type: str
    team_id: Optional[str] = None
    api_app_id: Optional[str] = None
    event: Optional[SlackEvent] = None
    event_id: Optional[str] = None
    event_time: Optional[int] = None
    authorizations: Optional[List[EventAuthorization]] = None
    is_ext_shared_channel: Optional[bool] = None
    event_context: Optional[str] = None
    challenge: Optional[str] = None

    @field_validator("event")
    def validate_event(cls, v: Optional[SlackEvent]) -> Optional[SlackEvent]:
        if v.type != "url_verification" and v is None:
            raise ValueError("event is required")
        return v


async def get_token() -> str:
    """Get the Slack bot token from the environment."""
    try:
        token = (
            marvin.settings.slack_api_token
        )  # set `MARVIN_SLACK_API_TOKEN` in `~/.marvin/.env
    except AttributeError:
        try:  # TODO: clean this up
            from prefect.blocks.system import Secret

            return (await Secret.load("slack-api-token")).get()
        except ImportError:
            pass
        token = os.getenv("MARVIN_SLACK_API_TOKEN")
        if not token:
            raise ValueError(
                "`MARVIN_SLACK_API_TOKEN` not found in environment."
                " Please set it in `~/.marvin/.env` or as an environment variable."
            )
    return token


def convert_md_links_to_slack(text) -> str:
    md_link_pattern = r"\[(?P<text>[^\]]+)]\((?P<url>[^\)]+)\)"

    # converting Markdown links to Slack-style links
    def to_slack_link(match):
        return f'<{match.group("url")}|{match.group("text")}>'

    # Replace Markdown links with Slack-style links
    slack_text = re.sub(md_link_pattern, to_slack_link, text)

    return slack_text


async def post_slack_message(
    message: str,
    channel_id: str,
    thread_ts: Union[str, None] = None,
    auth_token: Union[str, None] = None,
) -> httpx.Response:
    if not auth_token:
        auth_token = await get_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "channel": channel_id,
                "text": convert_md_links_to_slack(message),
                "thread_ts": thread_ts,
            },
        )

    response.raise_for_status()
    return response


async def get_thread_messages(channel: str, thread_ts: str) -> list:
    """Get all messages from a slack thread."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.replies",
            headers={"Authorization": f"Bearer {await get_token()}"},
            params={"channel": channel, "ts": thread_ts},
        )
    response.raise_for_status()
    return response.json().get("messages", [])


async def get_user_name(user_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/users.info",
            params={"user": user_id},
            headers={"Authorization": f"Bearer {await get_token()}"},  # noqa: E501
        )
    return (
        response.json().get("user", {}).get("name", user_id)
        if response.status_code == 200
        else user_id
    )


async def get_channel_name(channel_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.info",
            params={"channel": channel_id},
            headers={"Authorization": f"Bearer {await get_token()}"},  # noqa: E501
        )
    return (
        response.json().get("channel", {}).get("name", channel_id)
        if response.status_code == 200
        else channel_id
    )


async def fetch_current_message_text(channel: str, ts: str) -> str:
    """Fetch the current text of a specific Slack message using its timestamp."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.replies",
            params={"channel": channel, "ts": ts},
            headers={"Authorization": f"Bearer {await get_token()}"},  # noqa: E501
        )
    response.raise_for_status()
    messages = response.json().get("messages", [])
    if not messages:
        raise ValueError("Message not found")

    return messages[0]["text"]


async def edit_slack_message(
    new_text: str,
    channel_id: str,
    thread_ts: str,
    mode: str = "append",
    delimiter: Union[str, None] = None,
) -> httpx.Response:
    """Edit an existing Slack message by appending new text or replacing it.

    Args:
        channel (str): The Slack channel ID.
        ts (str): The timestamp of the message to edit.
        new_text (str): The new text to append or replace in the message.
        mode (str): The mode of text editing, 'append' (default) or 'replace'.

    Returns:
        httpx.Response: The response from the Slack API.
    """
    if mode == "append":
        current_text = await fetch_current_message_text(channel_id, thread_ts)
        delimiter = "\n\n" if delimiter is None else delimiter
        updated_text = f"{current_text}{delimiter}{convert_md_links_to_slack(new_text)}"
    elif mode == "replace":
        updated_text = convert_md_links_to_slack(new_text)
    else:
        raise ValueError("Invalid mode. Use 'append' or 'replace'.")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.update",
            headers={"Authorization": f"Bearer {await get_token()}"},
            json={"channel": channel_id, "ts": thread_ts, "text": updated_text},
        )

    response.raise_for_status()
    return response


async def search_slack_messages(
    query: str,
    max_messages: int = 3,
    channel: Union[str, None] = None,
    user_auth_token: Union[str, None] = None,
) -> list:
    """
    Search for messages in Slack workspace based on a query.

    Args:
        query (str): The search query.
        max_messages (int): The maximum number of messages to retrieve.
        channel (str, optional): The specific channel to search in. Defaults to None,
            which searches all channels.

    Returns:
        list: A list of message contents and permalinks matching the query.
    """
    all_messages = []
    next_cursor = None

    if not user_auth_token:
        user_auth_token = await get_token()

    async with httpx.AsyncClient() as client:
        while len(all_messages) < max_messages:
            params = {
                "query": query,
                "limit": min(max_messages - len(all_messages), 10),
            }
            if channel:
                params["channel"] = channel
            if next_cursor:
                params["cursor"] = next_cursor

            response = await client.get(
                "https://slack.com/api/search.messages",
                headers={"Authorization": f"Bearer {user_auth_token}"},
                params=params,
            )

            response.raise_for_status()
            data = response.json().get("messages", {}).get("matches", [])
            for message in data:
                all_messages.append(
                    {
                        "content": message.get("text", ""),
                        "permalink": message.get("permalink", ""),
                    }
                )

            next_cursor = (
                response.json().get("response_metadata", {}).get("next_cursor")
            )

            if not next_cursor:
                break

    return all_messages[:max_messages]


async def get_workspace_info(slack_bot_token: Union[str, None] = None) -> dict:
    if not slack_bot_token:
        slack_bot_token = await get_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/team.info",
            headers={"Authorization": f"Bearer {slack_bot_token}"},
        )
        response.raise_for_status()
        return response.json().get("team", {})
