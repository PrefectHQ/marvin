import base64
from io import BytesIO
from typing import Any, Dict

import httpx
import marvin
from marvin.api.threads import get_or_create_thread_by_lookup_key
from marvin.models.bots import BotConfigCreate, BotConfigUpdate
from marvin.models.threads import ThreadUpdate
from PIL import Image


def render_image(base64_image_str: str):
    image_bytes = base64.b64decode(base64_image_str)
    image = Image.open(BytesIO(image_bytes))
    image.show()


async def create_bot(bot_config: BotConfigCreate) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{marvin.settings.api_base_url}:{marvin.settings.api_port}/bots/",
            json=bot_config.dict(),
        )
        response.raise_for_status()
        return response


async def delete_bot(name: str):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{marvin.settings.api_base_url}:{marvin.settings.api_port}/bots/{name}",
        )
        response.raise_for_status()


async def get_bot(name: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{marvin.settings.api_base_url}:{marvin.settings.api_port}/bots/{name}",
        )
        response.raise_for_status()
        return response


async def update_bot(name: str, bot_config: BotConfigUpdate) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{marvin.settings.api_base_url}:{marvin.settings.api_port}/bots/{name}",
            json=bot_config.dict(),
        )
        response.raise_for_status()
        return response


async def talk_to_bot(
    name: str, message: str, thread_lookup_key: str = None
) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        payload = {"message": message}
        if thread_lookup_key:
            payload["thread_lookup_key"] = thread_lookup_key

        response = await client.post(
            f"{marvin.settings.api_base_url}:{marvin.settings.api_port}/bots/{name}",
            json=payload,
        )

        response.raise_for_status()

        return response


async def update_thread(thread_id: str, thread: ThreadUpdate) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{marvin.settings.api_base_url}:{marvin.settings.api_port}/threads/{thread_id}",
            json=thread.dict(),
        )
        response.raise_for_status()
        return response


if __name__ == "__main__":
    import asyncio
    import json

    # delete bot
    asyncio.run(delete_bot("marvin"))

    # create bot
    asyncio.run(create_bot(BotConfigCreate(name="marvin", personality="friendly")))

    # update bot personality
    asyncio.run(
        update_bot("marvin", BotConfigUpdate(name="marvin", personality="super angry"))
    )

    # get bot profile picture
    resp = asyncio.run(get_bot("marvin"))
    print(resp.json()["personality"])
    render_image(resp.json()["profile_picture"])

    # get or create thread
    resp = asyncio.run(get_or_create_thread_by_lookup_key("test"))
    thread_id = json.loads(resp.json())["id"]

    # update thread
    asyncio.run(update_thread(thread_id, ThreadUpdate(context={"test": "test"})))

    # talk to bot
    resp = asyncio.run(talk_to_bot("marvin", "hello", "test"))
    print(resp.json())
