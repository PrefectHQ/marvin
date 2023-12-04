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
    """Check if a given timestamp is in the Redis cache."""
    print(ts)
    print(redis_client.get(ts))
    if ts is None:
        return False
    return redis_client.exists(ts)


@app.post("/chat")
async def chat_endpoint(request: Request):
    payload = SlackPayload(**await request.json())

    logger.debug_kv("Handling slack message", payload, "green")

    match payload.type:
        case "event_callback":
            if payload.event.type == "reaction_added":
                if await reacted_to_bot(payload.event.item.get("ts")):
                    options = dict(
                        flow_run_name="handle reaction event",
                        retries=1,
                    )
                    emoji_name = payload.event.reaction
                    asyncio.create_task(
                        handle_reaction_added.with_options(**options)(
                            payload, emoji_name
                        )
                    )
            else:
                options = dict(
                    flow_run_name=f"respond in {payload.event.channel}",
                    retries=1,
                )
                asyncio.create_task(handle_message.with_options(**options)(payload))
        case "url_verification":
            return JSONResponse({"challenge": payload.challenge})
        case _:
            raise HTTPException(status_code=400, detail="Invalid event type")

    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4200)
