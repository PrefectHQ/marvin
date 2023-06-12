import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from prefect.blocks.core import Block
from prefect.events import emit_event
from prefect.utilities.collections import listrepr
from pydantic import BaseModel, ValidationError

import marvin
from marvin.config import CHROMA_INSTALLED
from marvin.utilities.meta import create_chroma_document
from marvin.utilities.strings import convert_md_links_to_slack, count_tokens
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(
    tags=["Slack"],
    prefix="/slack",
)

BOT_SLACK_ID = None

USER_CACHE = {}


class SlackEvent(BaseModel):
    type: str
    user: Optional[str]
    text: Optional[str]
    channel: Optional[str]
    ts: Optional[str]
    thread_ts: Optional[str] = None
    actions: Optional[List[Dict]] = None


class SlackAction(BaseModel):
    trigger_id: str
    user: Dict[str, str]
    container: Dict[str, str]
    actions: List[Dict[str, Any]]
    channel: Dict[str, str]


async def _slack_api_call(
    method: str,
    endpoint: str,
    json_data: Dict[str, Any] = None,
    params: Dict[str, str] = None,
    headers: Dict[str, str] = None,
) -> httpx.Response:
    if not headers:
        headers = {
            "Authorization": (
                f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
            ),
            "Content-Type": "application/json; charset=utf-8",
        }

    async with httpx.AsyncClient() as client:
        client_method = getattr(client, method.lower())
        if method.lower() == "get":
            response = await client_method(
                f"https://slack.com/api/{endpoint}", headers=headers, params=params
            )
        else:
            response = await client_method(
                f"https://slack.com/api/{endpoint}", headers=headers, json=json_data
            )

        marvin.get_logger().debug(f"Slack API call ({endpoint}): {response.json()}")
        response.raise_for_status()
        return response


async def _get_bot_user():
    response = await _slack_api_call("POST", "auth.test")
    response.raise_for_status()
    global BOT_SLACK_ID
    BOT_SLACK_ID = response.json().get("user_id", None)


async def _post_message(
    channel: str, message: str, thread_ts: str = None
) -> Dict[str, Any]:
    response = await _slack_api_call(
        "POST",
        "chat.postMessage",
        json_data={
            "channel": channel,
            "text": convert_md_links_to_slack(message),
            **({"thread_ts": thread_ts} if thread_ts else {}),
        },
    )
    return response.json()


async def _post_QA_message(
    channel: str,
    question: str,
    answer: str,
    asking_user: str,
    origin_channel: str,
    origin_ts: str = None,
) -> Dict[str, Any]:
    formatted_message = (
        f":bangbang: `<@{asking_user}>` tagged marvin :bangbang:\n\n"
        f"*Prompt:*\n{question}\n\n"
        f"*Marvin answered with*:\n{answer}\n\n"
    )

    response = await _post_message(
        channel=channel,
        message=formatted_message,
    )

    if response.get("ok"):
        action_value = json.dumps(
            {
                "channel": channel,
                "question": question,
                "proposed_answer": answer,
                "asking_user": asking_user,
                "origin_channel": origin_channel,
                "origin_ts": origin_ts,
            }
        )
        # Add the buttons to the QA message
        await _slack_api_call(
            "POST",
            "chat.update",
            json_data={
                "channel": channel,
                "ts": response["ts"],
                "text": formatted_message,
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": formatted_message},
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve Response"},
                            "action_id": "approve_response",
                            "value": action_value,
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Edit Response"},
                                "action_id": "edit_response",
                                "value": action_value,
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Discard"},
                                "action_id": "discard",
                                "value": action_value,
                            },
                        ],
                    },
                ],
            },
        )

    return response


async def _handle_edit_response_submission(
    editing_user: str,
    new_message: str,
    qa_channel: str,
    private_metadata: dict,
):
    action_value = json.dumps(
        {
            "editing_user": editing_user,
            "asking_user": private_metadata["asking_user"],
            "question": private_metadata["question"],
            "proposed_answer": new_message,
            "channel": private_metadata["channel"],
            "origin_ts": private_metadata["origin_ts"],
        }
    )

    # update Marvin's answer to the user
    await _slack_api_call(
        "POST",
        "chat.update",
        json_data={
            "channel": private_metadata["origin_channel"],
            "ts": private_metadata["origin_ts"],
            "text": f"*Edited by <@{editing_user}>*: {new_message}",
        },
    )

    # update the QA message
    await _slack_api_call(
        "POST",
        "chat.update",
        json_data={
            "channel": qa_channel,
            "ts": private_metadata["qa_message_ts"],
            "text": f"*Edited*: {new_message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*<@{editing_user}> edited Marvin's"
                            f" response*:\n{new_message}"
                        ),
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": marvin.settings.feedback_mechanism.replace(
                                "_", " "
                            ).title(),
                        },
                        "action_id": "approve_response",
                        "value": action_value,
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Discard"},
                            "action_id": "discard",
                            "value": action_value,
                        },
                    ],
                },
            ],
        },
    )


async def _handle_view_submission(payload: Dict[str, Any]):
    view = payload["view"]
    editing_user = payload["user"]
    values = view["state"]["values"]
    response_input = None
    qa_channel = None

    for block_id, block_values in values.items():
        for action_id, action_values in block_values.items():
            if action_id == "response_input":
                response_input = action_values["value"]
                qa_channel = block_id

    if view["callback_id"] == "edit_response_modal":
        await _handle_edit_response_submission(
            editing_user["id"],
            response_input,
            qa_channel,
            json.loads(view["private_metadata"]),
        )


async def _handle_discard(action: SlackAction):
    action_value = json.loads(action.actions[0]["value"])

    # Update the QA message
    await _slack_api_call(
        "POST",
        "chat.update",
        json_data={
            "channel": action.channel["id"],
            "ts": action.container["message_ts"],
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":bangbang: `<@{action_value.get('asking_user')}>` asked a"
                            " question"
                            f" :bangbang:\n\n*Question:*\n{action_value['question']}\n\n*Marvin"  # noqa
                            " proposed an"
                            f" answer*:\n{action_value['proposed_answer']}\n\n:wastebasket:"  # noqa
                            " Discarded"
                        ),
                    },
                }
            ],
        },
    )


async def _show_edit_response_modal(action_event: SlackAction) -> Dict[str, Any]:
    action_value = json.loads(action_event.actions[0]["value"])

    return await _slack_api_call(
        "POST",
        "views.open",
        json_data={
            "trigger_id": action_event.trigger_id,
            "view": {
                "type": "modal",
                "callback_id": "edit_response_modal",
                "title": {"type": "plain_text", "text": "Edit Response"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": action_event.channel["id"],
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "response_input",
                            "multiline": True,
                            "initial_value": action_value["proposed_answer"],
                        },
                        "label": {"type": "plain_text", "text": "Edited Response"},
                    }
                ],
                "private_metadata": json.dumps(
                    {
                        "asking_user": action_value["asking_user"],
                        "qa_message_ts": action_event.container["message_ts"],
                        "question": action_value["question"],
                        "channel": action_event.channel["id"],
                        "origin_channel": action_value["origin_channel"],
                        "origin_ts": action_value["origin_ts"],
                    }
                ),
                "submit": {"type": "plain_text", "text": "Submit"},
            },
        },
    )


async def _handle_approve_response(action: SlackAction):
    action_value = json.loads(action.actions[0]["value"])
    asking_user = action_value.get("asking_user")
    editing_user = action.user["id"]

    question_answer = f"""**{action_value["question"]}**\n\n
    
    {action_value["proposed_answer"]}
    """  # noqa

    # creates and saves a document to chroma
    if CHROMA_INSTALLED:
        await create_chroma_document(text=question_answer)
    else:
        await _post_message(
            channel=action.channel["id"],
            message=(  # noqa
                f"hey <@{marvin.settings.slack_bot_admin_user}, I can't use Chroma -"
                " did you install it on my machine?"
            ),
            thread_ts=action.container["message_ts"],
        )

    await _slack_api_call(
        "POST",
        "chat.update",
        json_data={
            "channel": action.channel["id"],
            "ts": action.container["message_ts"],
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":bangbang: `<@{asking_user}>` asked a question"
                            f" :bangbang:\n\n*Question:*\n{action_value['question']}\n\n*<@{editing_user}>"  # noqa
                            " provided and/or approved an"
                            f" answer*:\n{action_value['proposed_answer']}\n\n:white_check_mark:"  # noqa
                            " Feedback recorded"
                        ),
                    },
                }
            ],
        },
    )


async def _slackbot_response(event: SlackEvent):
    try:
        marvin.get_logger().info(marvin.settings.slack_bot_name)
        bot = await marvin.Bot.load(marvin.settings.slack_bot_name)
    except HTTPException as e:
        if e.status_code == 404:
            marvin.get_logger().warning(msg := "Slackbot not configured")
            await _post_message(
                channel=event.channel,
                message=(
                    "So this is what death is like... pls"
                    f" <{marvin.settings.slack_bot_admin_user}> revive me :pray:"
                ),
                thread_ts=event.ts,
            )
            raise UserWarning(msg)
        else:
            raise

    thread = event.thread_ts or event.ts
    await bot.set_thread(thread_lookup_key=f"{event.channel}:{thread}")

    text = event.text.replace(f"<@{BOT_SLACK_ID}>", bot.name).strip()
    response = await bot.say(text)

    slack_response = await _post_message(
        channel=event.channel, message=response.content, thread_ts=event.ts
    )

    response_ts = slack_response.get("ts")
    prompt_tokens = count_tokens(text)
    response_tokens = count_tokens(response.content)

    # this will do nothing if Prefect credentials are not configured
    emit_event(
        event=f"bot.{bot.name.lower()}.responded",
        resource={"prefect.resource.id": f"bot.{bot.name.lower()}"},
        payload={
            "user": event.user,
            "channel": event.channel,
            "thread_ts": thread,
            "text": text,
            "response": response.content,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": prompt_tokens + response_tokens,
        },
    )

    if marvin.settings.QA_slack_bot_responses:
        await _post_QA_message(
            channel=marvin.settings.slack_bot_QA_channel or event.channel,
            question=text,
            answer=response.content,
            asking_user=event.user,
            origin_channel=event.channel,
            origin_ts=response_ts,
        )


async def _save_thread_to_discourse(payload: Dict[str, Any]):
    thread_ts = payload["message"]["thread_ts"]
    channel_id = payload["channel"]["id"]
    user_id = payload["user"]["id"]

    allowed_users = await Block.load("json/allowed-qa-users")

    if user_id not in allowed_users.value.values():
        dm_channel_response = await _slack_api_call(
            "POST", "conversations.open", json_data={"users": user_id}
        )
        dm_channel_id = dm_channel_response.json()["channel"]["id"]

        # Send a message to the DM channel
        await _post_message(
            channel=dm_channel_id,
            message=(
                "Sorry, you're not allowed to take that action :cry:"
                f" \n\nPlease contact <@{marvin.settings.slack_bot_admin_user}>"
                " if this is a mistake - thank you :slightly_smiling_face:"
                " \n\n[here's a duck](https://random-d.uk/) for your troubles."
            ),
        )
        return

    history = await _slack_api_call(
        "GET", "conversations.replies", params={"channel": channel_id, "ts": thread_ts}
    )
    thread_messages = history.json().get("messages", [])

    thread_text = ""
    for message in thread_messages:
        global USER_CACHE
        if message["user"] in USER_CACHE:
            username = USER_CACHE[message["user"]]
        else:
            user_info = await _slack_api_call(
                "GET", "users.info", params={"user": message["user"]}
            )
            username = user_info.json().get("user", {}).get("name", "unknown user")
            USER_CACHE[message["user"]] = username

        # skip the bot's messages that don't have a green checkmark emoji
        if user_info.json().get("user", {}).get("id") == BOT_SLACK_ID:
            reactions = message.get("reactions", [])
            if not any(
                reaction
                for reaction in reactions
                if reaction["name"] == "white_check_mark"
            ):
                continue

        thread_text += f"{username}: {message['text']}\n\n"

    try:
        new_topic_url = await marvin.utilities.meta.create_discourse_topic(
            text=thread_text
        )
    except ValidationError as e:
        failed_fields = [err["loc"][0] for err in e.errors()]
        await _post_message(
            channel=channel_id,
            message=(
                f"Sorry, <@{user_id}>. I couldn't save this thread to Discourse because"
                f" I can't identify reasonable values for: {listrepr(failed_fields)}"
                " from the messages in this thread."
            ),
            thread_ts=thread_ts,
        )
        return

    await _post_message(
        channel=channel_id,
        message=(
            f"thanks to <@{user_id}> :slightly_smiling_face:, this thread has been"
            f" saved to Discourse.\n\nYou can find it here: {new_topic_url}"
        ),
        thread_ts=thread_ts,
    )


async def _keyword_response_handler(event: SlackEvent):
    try:
        keywords_block = await Block.load("json/marvin-slack-keyword-responses")
    except HTTPException as e:
        if e.status_code == 404:
            raise UserWarning("marvin-slack-keyword-responses block not found")
        else:
            raise

    matched_keywords = [
        keyword for keyword in keywords_block.value if keyword in event.text.lower()
    ]

    for keyword in matched_keywords:
        response = await Block.load(f"string/{keywords_block.value[keyword]}")
        await _post_message(
            channel=event.channel,
            message=response.value,
            thread_ts=event.ts,
        )


block_action_to_handler = {
    "approve_response": _handle_approve_response,
    "edit_response": _show_edit_response_modal,
    "discard": _handle_discard,
}


@router.post("/events", status_code=status.HTTP_200_OK)
async def handle_app_mentions(request: Request):
    """This route handles Slack events."""
    payload = await request.json()

    if payload["type"] == "url_verification":
        return payload["challenge"]

    if "event" in payload:
        event = SlackEvent(**payload["event"])

        if event.type == "app_mention":
            asyncio.ensure_future(_slackbot_response(event))
        elif event.type == "message" and event.text and event.user != BOT_SLACK_ID:
            asyncio.ensure_future(_keyword_response_handler(event))

    return {"success": True}


@router.post("/block_actions", status_code=status.HTTP_200_OK)
async def handle_block_actions(request: Request):
    form_data = await request.form()
    payload = json.loads(form_data["payload"])

    if payload.get("type") == "block_actions":
        action_event = SlackAction(**payload)
        asyncio.ensure_future(
            block_action_to_handler[action_event.actions[0]["action_id"]](action_event)
        )

    elif payload.get("type") == "view_submission":
        asyncio.ensure_future(_handle_view_submission(payload))

    elif payload.get("type") == "message_action":
        asyncio.ensure_future(_save_thread_to_discourse(payload))

    return JSONResponse(content={}, status_code=status.HTTP_200_OK)


async def startup():
    if marvin.settings.slack_api_token.get_secret_value():
        await _get_bot_user()
