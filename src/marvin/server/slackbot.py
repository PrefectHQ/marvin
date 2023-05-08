import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import marvin
from marvin.utilities.strings import convert_md_links_to_slack
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(
    tags=["Slack"],
    prefix="/slack",
)

BOT_SLACK_ID = None


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
    method: str, endpoint: str, json_data: Dict[str, Any]
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {marvin.settings.slack_api_token.get_secret_value()}",
        "Content-Type": "application/json; charset=utf-8",
    }

    async with httpx.AsyncClient() as client:
        client_method = getattr(client, method.lower())
        response = await client_method(
            f"https://slack.com/api/{endpoint}", headers=headers, json=json_data
        )
        marvin.get_logger().debug(f"Slack API call ({endpoint}): {response.json()}")
        response.raise_for_status()
        return response.json()


async def _get_bot_user():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/users.identity",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                ),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        global BOT_SLACK_ID
        BOT_SLACK_ID = response.json().get("user", {}).get("id", None)


async def _post_message(
    channel: str, message: str, thread_ts: str = None
) -> Dict[str, Any]:
    return await _slack_api_call(
        "POST",
        "chat.postMessage",
        json_data={
            "channel": channel,
            "text": convert_md_links_to_slack(message),
            **({"thread_ts": thread_ts} if thread_ts else {}),
        },
    )


async def _post_QA_message(
    channel: str,
    question: str,
    answer: str,
    user: str,
    origin_ts: str = None,
) -> Dict[str, Any]:
    formatted_message = (
        f":bangbang: `<@{user}>` asked a question :bangbang:\n\n"
        f"*Question:*\n{question}\n\n"
        f"*Marvin proposed an answer*:\n{answer}\n\n"
    )

    response = await _post_message(
        channel=channel,
        message=formatted_message,
    )

    if response.get("ok"):
        action_value = json.dumps(
            {
                "user": user,
                "channel": channel,
                "proposed_answer": answer,
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
                        ],
                    },
                ],
            },
        )

    return response


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

    if marvin.settings.QA_slack_bot_responses:
        return await _post_QA_message(
            channel=event.channel,
            question=text,
            answer=response.content,
            user=event.user,
            origin_ts=event.ts,
        )

    return await _post_message(
        channel=event.channel, message=response.content, thread_ts=event.ts
    )


async def _handle_approve_response(action: SlackAction):
    action_value = json.loads(action.actions[0]["value"])
    print("HI\n\n")

    print(action_value)

    # Send the approved message to the user thread
    await _post_message(
        channel=action_value["origin_channel"],
        message=action_value["proposed_answer"],
        thread_ts=action_value["origin_ts"],
    )


async def _handle_edit_response_submission(
    user: str,
    new_message: str,
    qa_channel: str,
    private_metadata: dict,
):
    return await _slack_api_call(
        "POST",
        "chat.update",
        json_data={
            "channel": qa_channel,
            "ts": private_metadata["qa_message_ts"],
            "text": f"*Edited*: {new_message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Edited*: {new_message}"},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve Response"},
                        "action_id": "approve_response",
                        "value": json.dumps(
                            {
                                "user": user,
                                "proposed_answer": new_message,
                                "origin_channel": private_metadata["origin_channel"],
                                "origin_ts": private_metadata["origin_ts"],
                            }
                        ),
                    },
                }
            ],
        },
    )


async def _handle_view_submission(payload: Dict[str, Any]):
    view = payload["view"]
    user = payload["user"]
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
            user["id"], response_input, qa_channel, json.loads(view["private_metadata"])
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
                        "qa_message_ts": action_event.container["message_ts"],
                        "origin_channel": action_event.channel["id"],
                        "origin_ts": action_event.actions[0]["action_ts"],
                    }
                ),
                "submit": {"type": "plain_text", "text": "Submit"},
            },
        },
    )


@router.post("/events", status_code=status.HTTP_200_OK)
async def handle_slack_events(request: Request):
    """This route handles Slack events."""
    payload = await request.json()

    if payload["type"] == "url_verification":
        return payload["challenge"]

    if "event" in payload:
        event = SlackEvent(**payload["event"])

        if event.type == "app_mention":
            asyncio.ensure_future(_slackbot_response(event))

    return {"success": True}


@router.post("/block_actions", status_code=status.HTTP_200_OK)
async def handle_block_actions(request: Request):
    form_data = await request.form()
    payload = json.loads(form_data["payload"])

    if payload.get("type") == "block_actions":
        action_event = SlackAction(**payload)
        if action_event.actions[0]["action_id"] == "approve_response":
            asyncio.ensure_future(_handle_approve_response(action_event))
        elif action_event.actions[0]["action_id"] == "edit_response":
            asyncio.ensure_future(_show_edit_response_modal(action_event))

    elif payload.get("type") == "view_submission":
        await _handle_view_submission(payload)

    return JSONResponse(content={}, status_code=status.HTTP_200_OK)


async def startup():
    if marvin.settings.slack_api_token.get_secret_value():
        await _get_bot_user()
