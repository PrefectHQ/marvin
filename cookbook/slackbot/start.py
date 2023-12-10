import asyncio
import json

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from flows import handle_dalle_slash_command, handle_message, handle_reaction_added
from marvin.utilities.logging import get_logger
from marvin.utilities.redis import redis_client
from marvin.utilities.slack import (
    SlackInteractionPayload,
    SlackPayload,
    SlackSlashCommandPayload,
    post_slack_message,
)
from starlette.responses import JSONResponse

app = FastAPI()
logger = get_logger("slackbot.app")


async def reacted_to_bot(ts: str | None) -> bool:
    """Check if a reaction is to a message sent by the bot."""
    try:
        async with redis_client() as _redis:
            logger.debug_kv("Checking if reacted to bot", ts, "green")
            return ts is not None and _redis.get(f"message:{ts}") == "true"
    except Exception as e:
        logger.error_kv("Failed to check if reacted to bot", e, "red")
        return False


@app.post("/chat")
async def chat_endpoint(request: Request) -> JSONResponse:
    payload = SlackPayload(**await request.json())
    logger.debug_kv("Handling slack message", payload, "green")

    match payload.type:
        case "event_callback":
            if payload.event.type == "reaction_added" and await reacted_to_bot(
                payload.event.item.get("ts")
            ):
                asyncio.create_task(
                    handle_reaction_added.with_options(flow_run_name="reaction added")(
                        payload, payload.event.reaction
                    )
                )
            elif payload.event.type != "reaction_added" and payload.mentions_bot():
                options = {
                    "flow_run_name": f"respond in {payload.event.channel}",
                    "retries": 1,
                }
                asyncio.create_task(handle_message.with_options(**options)(payload))
        case "url_verification":
            return JSONResponse({"challenge": payload.challenge})
        case _:
            raise HTTPException(status_code=400, detail="Invalid event type")

    return JSONResponse({"status": "ok"})


@app.post("/dalle")
async def generate_dalle_image(request: Request) -> str:
    payload = SlackSlashCommandPayload.from_form(await request.form())
    logger.debug_kv("Handling dalle request", payload, "green")

    if not payload.command == "/dalle":
        raise HTTPException(status_code=400, detail="Invalid command")

    asyncio.create_task(handle_dalle_slash_command(payload))

    return "Generating image(s)..."


@app.post("/slack/interactions")
async def handle_slack_interactions(request: Request) -> JSONResponse:
    form_data = await request.form()
    interaction_data = SlackInteractionPayload.from_json(form_data["payload"])

    action = interaction_data.actions[0]
    selected_image_url = action.value

    if action.action_id.startswith("select_image_"):
        private_metadata = json.loads(interaction_data.view.private_metadata)
        channel_id = private_metadata.get("channel_id")
        user_prompt = private_metadata.get("user_prompt")

        if channel_id:
            await post_slack_message(
                message=f"[{user_prompt}]({selected_image_url})",
                channel_id=channel_id,
            )
            return JSONResponse({"response_action": "close"})
        else:
            raise HTTPException(status_code=400, detail="Channel ID not found")

    raise HTTPException(status_code=400, detail="Invalid action")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
