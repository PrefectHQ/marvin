import json
import os
import re
from typing import Optional, Union

import httpx
from pydantic import BaseModel, field_validator

import marvin
from marvin.utilities.logging import get_logger

SLACKBOT_MENTION = r"<@(\w+)>"


class EventBlockElement(BaseModel):
    type: str
    text: Optional[str] = None
    user_id: Optional[str] = None


class EventBlockElementGroup(BaseModel):
    type: str
    elements: list[EventBlockElement]


class EventBlock(BaseModel):
    type: str
    block_id: str
    elements: list[Union[EventBlockElement, EventBlockElementGroup]]


class ReactionAddedEvent(BaseModel):
    type: str
    user: str
    reaction: str
    item_user: str
    item: dict  # You can further define this field if needed
    event_ts: str


class SlackEvent(BaseModel):
    client_msg_id: Optional[str] = None
    type: str
    text: Optional[str] = None
    user: Optional[str] = None
    ts: Optional[str] = None
    team: Optional[str] = None
    channel: Optional[str] = None
    event_ts: Optional[str] = None
    thread_ts: Optional[str] = None
    parent_user_id: Optional[str] = None
    blocks: Optional[list[EventBlock]] = None
    reaction: Optional[str] = None
    item_user: Optional[str] = None
    item: Optional[dict] = None  # You can further define this field if needed


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
    event: Optional[Union[SlackEvent, ReactionAddedEvent]] = None
    event_id: Optional[str] = None
    event_time: Optional[int] = None
    authorizations: Optional[list[EventAuthorization]] = None
    is_ext_shared_channel: Optional[bool] = None
    event_context: Optional[str] = None
    challenge: Optional[str] = None

    @field_validator("event")
    def validate_event(cls, v: Optional[SlackEvent]) -> Optional[SlackEvent]:
        if v.type != "url_verification" and v is None:
            raise ValueError("event is required")
        return v

    def mentions_bot(self, bot_mention_pattern: str = SLACKBOT_MENTION) -> bool:
        """Check if the message is addressed to the bot."""
        if self.event:
            user = re.search(bot_mention_pattern, self.event.text or "")
            if user and user.group(1) == self.authorizations[0].user_id:
                return True
        return False


class SlackSlashCommandPayload(BaseModel):
    token: str
    team_id: str
    team_domain: str
    enterprise_id: Optional[str] = None
    enterprise_name: Optional[str] = None
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str
    trigger_id: str
    api_app_id: str

    @classmethod
    def from_form(cls, formdata):
        return cls(**dict(formdata))


class SlackInteractionUser(BaseModel):
    id: str
    username: Optional[str] = None
    name: Optional[str] = None
    team_id: str


class SlackInteractionTeam(BaseModel):
    id: str
    domain: Optional[str] = None


class SlackInteractionAction(BaseModel):
    action_id: str
    block_id: str
    value: str
    type: str
    action_ts: Optional[str] = None


class SlackInteractionView(BaseModel):
    id: str
    team_id: str
    type: str
    blocks: Optional[list[dict]] = None
    private_metadata: Optional[str] = None
    callback_id: Optional[str] = None
    state: Optional[dict] = None
    hash: Optional[str] = None
    title: Optional[dict] = None
    clear_on_close: Optional[bool] = None
    notify_on_close: Optional[bool] = None
    close: Optional[dict] = None
    submit: Optional[dict] = None
    previous_view_id: Optional[str] = None
    root_view_id: Optional[str] = None
    app_id: Optional[str] = None
    external_id: Optional[str] = None
    app_installed_team_id: Optional[str] = None
    bot_id: Optional[str] = None


class SlackInteractionPayload(BaseModel):
    type: str
    token: str
    user: SlackInteractionUser
    team: SlackInteractionTeam
    api_app_id: str
    trigger_id: str
    actions: list[SlackInteractionAction]
    view: SlackInteractionView
    container: Optional[dict[str, str]] = None
    enterprise: Optional[dict[str, str]] = None
    is_enterprise_install: Optional[bool] = None

    @classmethod
    def from_json(cls, json_data: str):
        return cls(**json.loads(json_data))


async def get_token() -> str:
    """Get the Slack bot token from the environment."""
    try:
        token = marvin.settings.slack_api_token
    except AttributeError:
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


async def get_emoji(emoji_name: str, token: str | None = None) -> str:
    try:
        import emoji

        standard_emoji = emoji.emojize(f":{emoji_name}:", language="alias")
        if standard_emoji != f":{emoji_name}:":
            return standard_emoji
    except ImportError:
        get_logger("marvin.utilities.slack").debug_kv(
            "ImportError", "install `emoji` via `pip install emoji`", "red"
        )
        pass

    if not token:
        token = await get_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/emoji.list",
            headers={"Authorization": f"Bearer {token}"},
        )
        emojis = response.json().get("emoji", {})
        custom_emoji = emojis.get(emoji_name, "")
        if custom_emoji:
            return custom_emoji

    raise ValueError(f"Emoji {emoji_name} not found.")


async def open_modal(
    trigger_id: str,
    blocks: list[dict],
    private_metadata: Optional[str] = None,
    title: str = "Modal",
) -> httpx.Response:
    """
    Opens a modal in Slack using the views.open method.

    Args:
        trigger_id (str): The trigger ID received from the slash command payload.
        blocks (list[dict]): The blocks to display in the modal.

    Returns:
        httpx.Response: The response from the Slack API.
    """
    modal_view = {
        "type": "modal",
        "callback_id": (
            "modal-identifier"
        ),  # You can customize this ID for handling in your interactions endpoint
        "title": {"type": "plain_text", "text": title},
        "blocks": blocks,
        **({"private_metadata": private_metadata} if private_metadata else {}),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/views.open",
            headers={"Authorization": f"Bearer {await get_token()}"},
            json={"trigger_id": trigger_id, "view": modal_view},
        )

    response.raise_for_status()
    return response


async def update_modal(
    view_id: str,
    blocks: list[dict],
    private_metadata: Optional[str] = None,
    title: str = "Updated Modal",
) -> httpx.Response:
    """
    Update an existing modal in Slack using the views.update method.

    Args:
        view_id (str): The ID of the view (modal) to be updated.
        blocks (list[dict]): The blocks to display in the updated modal.
        token (str): Slack Bot User OAuth Access Token.

    Returns:
        httpx.Response: The response from the Slack API.
    """
    update_payload = {
        "view_id": view_id,
        "view": {
            "type": "modal",
            "title": {"type": "plain_text", "text": title},
            "blocks": blocks,
            **({"private_metadata": private_metadata} if private_metadata else {}),
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/views.update",
            headers={"Authorization": f"Bearer {await get_token()}"},
            json=update_payload,
        )

    response.raise_for_status()
    return response
