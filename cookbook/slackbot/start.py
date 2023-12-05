import asyncio

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from flows import handle_message, handle_reaction_added
from marvin.utilities.logging import get_logger
from marvin.utilities.slack import SlackPayload
from starlette.responses import JSONResponse

app = FastAPI()
logger = get_logger("slackbot.app")
redis_client = redis.StrictRedis(host="redis", port=6379, db=0, decode_responses=True)


async def reacted_to_bot(ts: str | None) -> bool:
    """Check if a reaction is to a message sent by the bot."""
    logger.debug_kv("Checking if reacted to bot", ts, "green")
    return ts is not None and redis_client.get(f"message:{ts}") == "true"


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
