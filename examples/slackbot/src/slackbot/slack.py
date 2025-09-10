"""Module for Slack-related utilities."""

import re
from typing import Any, List, Union

import httpx
from pydantic import BaseModel, ValidationInfo, field_validator, model_validator

from slackbot.settings import settings


class EventBlockElement(BaseModel):
    type: str
    text: str | None = None
    user_id: str | None = None


class EventBlockElementGroup(BaseModel):
    type: str
    elements: List[EventBlockElement]


class EventBlock(BaseModel):
    type: str
    block_id: str
    elements: List[Union[EventBlockElement, EventBlockElementGroup]]


class SlackEvent(BaseModel):
    client_msg_id: str | None = None
    type: str
    subtype: str | None = None
    text: str | None = None
    # For message_changed edit events, Slack nests the edited message here
    message: dict[str, Any] | None = None
    user: str | dict[str, Any] | None = None
    ts: str | None = None
    team: str | None = None
    channel: str | None = None
    event_ts: str
    thread_ts: str | None = None
    parent_user_id: str | None = None
    blocks: list[EventBlock] | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_user_id(cls, data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data.get("user"), dict):
            data["user"] = data["user"].get("id")
        return data


class EventAuthorization(BaseModel):
    enterprise_id: str | None = None
    team_id: str
    user_id: str
    is_bot: bool
    is_enterprise_install: bool


class SlackPayload(BaseModel):
    token: str
    type: str
    team_id: str | None = None
    api_app_id: str | None = None
    event: SlackEvent | None = None
    event_id: str | None = None
    event_time: int | None = None
    authorizations: list[EventAuthorization] | None = None
    is_ext_shared_channel: bool | None = None
    event_context: str | None = None
    challenge: str | None = None

    @field_validator("event")
    def validate_event(
        cls, v: SlackEvent | None, info: ValidationInfo
    ) -> SlackEvent | None:
        if v is None and info.data.get("type") != "url_verification":
            raise ValueError("event is required")
        return v


def convert_md_links_to_slack(text: str) -> str:
    md_link_pattern = r"\[(?P<text>[^\]]+)]\((?P<url>[^\)]+)\)"

    # converting Markdown links to Slack-style links
    def to_slack_link(match: re.Match[str]) -> str:
        return f"<{match.group('url')}|{match.group('text')}>"

    # Replace Markdown links with Slack-style links
    return re.sub(
        r"\*\*(.*?)\*\*", r"*\1*", re.sub(md_link_pattern, to_slack_link, text)
    )


async def post_slack_message(
    message: str,
    channel_id: str,
    attachments: list[dict[str, Any]] | None = None,
    thread_ts: str | None = None,
) -> httpx.Response:
    post_data = {
        "channel": channel_id,
        "text": convert_md_links_to_slack(message),
        "attachments": attachments if attachments else [],
    }

    if thread_ts:
        post_data["thread_ts"] = thread_ts

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.slack_api_token}"},
            json=post_data,
        )
        response_data = response.json()

    if response_data.get("ok") is not True:
        raise ValueError(f"Error posting Slack message: {response_data.get('error')}")
    return response


async def get_thread_messages(
    channel: str, thread_ts: str, auth_token: str
) -> list[dict[str, Any]]:
    """Get all messages from a slack thread."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.replies",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"channel": channel, "ts": thread_ts},
        )
    response.raise_for_status()
    return response.json().get("messages", [])


async def get_user_name(user_id: str) -> str:
    async with httpx.AsyncClient() as client:
        auth_token = settings.slack_api_token
        response = await client.get(
            "https://slack.com/api/users.info",
            params={"user": user_id},
            headers={"Authorization": f"Bearer {auth_token}"},
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
            headers={"Authorization": f"Bearer {settings.slack_api_token}"},
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
            headers={"Authorization": f"Bearer {settings.slack_api_token}"},
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
            headers={"Authorization": f"Bearer {settings.slack_api_token}"},
            json={"channel": channel_id, "ts": thread_ts, "text": updated_text},
        )

    response.raise_for_status()
    return response


async def search_slack_messages(
    query: str,
    max_messages: int = 3,
    channel: str | None = None,
) -> list[dict[str, Any]]:
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
    all_messages: list[dict[str, Any]] = []
    next_cursor = None

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
                headers={"Authorization": f"Bearer {settings.slack_api_token}"},
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


async def get_workspace_info() -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/team.info",
            headers={"Authorization": f"Bearer {settings.slack_api_token}"},
        )
        response.raise_for_status()
        return response.json().get("team", {})


async def get_workspace_domain() -> str:
    """Get the workspace domain name (e.g., 'stoatllc')."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/team.info",
            headers={"Authorization": f"Bearer {settings.slack_api_token}"},
        )
        response.raise_for_status()
        team_info = response.json().get("team", {})
        return team_info.get("domain", "unknown")


class ProgressMessage:
    """Utility for creating and updating a progress message in Slack."""

    def __init__(self, channel_id: str, thread_ts: str | None = None):
        self.channel_id = channel_id
        self.thread_ts = thread_ts
        self.message_ts: str | None = None

    async def start(self, initial_text: str = "🔄 Working...") -> "ProgressMessage":
        """Create the initial progress message and return its timestamp."""
        response = await post_slack_message(
            message=initial_text,
            channel_id=self.channel_id,
            thread_ts=self.thread_ts,
        )

        response_data = response.json()
        if response_data.get("ok"):
            self.message_ts = response_data.get("ts")
        else:
            raise ValueError(
                f"Failed to create progress message: {response_data.get('error')}"
            )

        return self

    async def update(self, new_text: str, mode: str = "replace") -> None:
        """Update the progress message."""
        if not self.message_ts:
            raise ValueError("Progress message not started. Call start() first.")

        await edit_slack_message(
            new_text=new_text,
            channel_id=self.channel_id,
            thread_ts=self.message_ts,
            mode=mode,
        )

    async def append(self, text: str, delimiter: str = "\n") -> None:
        """Append text to the progress message."""
        if not self.message_ts:
            raise ValueError("Progress message not started. Call start() first.")

        await edit_slack_message(
            new_text=text,
            channel_id=self.channel_id,
            thread_ts=self.message_ts,
            mode="append",
            delimiter=delimiter,
        )


async def create_progress_message(
    channel_id: str, thread_ts: str | None = None, initial_text: str = "🔄 Working..."
) -> ProgressMessage:
    """Helper function to create and start a progress message."""
    progress = ProgressMessage(channel_id, thread_ts)
    await progress.start(initial_text)
    return progress
