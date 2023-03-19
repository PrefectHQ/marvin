import asyncio
import random

import httpx
import sqlalchemy as sa
from fastapi import BackgroundTasks, Body, Depends, HTTPException, status

import marvin
from marvin.api.dependencies import fastapi_session
from marvin.infra.db import AsyncSession, provide_session
from marvin.models.bots import (
    BotConfig,
    BotConfigCreate,
    BotConfigUpdate,
)
from marvin.models.threads import Message, ThreadCreate
from marvin.utilities.types import MarvinRouter

router = MarvinRouter(prefix="/bots", tags=["Bot Configs"])


@router.post("/", status_code=status.HTTP_201_CREATED)
@provide_session()
async def create_bot_config(
    bot_config: BotConfigCreate,
    session: AsyncSession = Depends(fastapi_session),
    background_tasks: BackgroundTasks = None,
) -> BotConfig:
    session.add(bot_config)
    await session.commit()

    # generate a profile picture
    if marvin.settings.bot_create_profile_picture:
        if background_tasks:
            background_tasks.add_task(
                _create_bot_config_profile_picture, bot_name=bot_config.name
            )
        else:
            asyncio.ensure_future(
                _create_bot_config_profile_picture(bot_name=bot_config.name)
            )

    return bot_config


@router.get("/{name}")
@provide_session()
async def get_bot_config(
    name: str,
    session: AsyncSession = Depends(fastapi_session),
) -> BotConfig | None:
    result = await session.execute(
        sa.select(BotConfig).where(BotConfig.name == name).limit(1)
    )
    bot_config = result.scalar()
    if not bot_config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Bot "{name}" not found')
    return bot_config


@router.patch("/{name}", status_code=status.HTTP_204_NO_CONTENT)
@provide_session()
async def update_bot_config(
    name: str,
    bot_config: BotConfigUpdate,
    session: AsyncSession = Depends(fastapi_session),
):
    await session.execute(
        sa.update(BotConfig)
        .where(BotConfig.name == name)
        .values(**bot_config.dict(exclude_unset=True))
    )
    await session.commit()


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
@provide_session()
async def delete_bot_config(
    name: str,
    session: AsyncSession = Depends(fastapi_session),
):
    await session.execute(sa.delete(BotConfig).where(BotConfig.name == name))
    await session.commit()


@router.post("/{name}", status_code=status.HTTP_201_CREATED)
@provide_session()
async def talk_to_bot(
    name: str,
    message: str = Body(embed=True),
    thread_lookup_key: str = None,
    session: AsyncSession = Depends(fastapi_session),
) -> Message:
    """
    Convenience method to talk to a bot.

    Equivalent to creating a new thread, adding the bot, then sending a message
    to the thread.
    """
    bot = await marvin.Bot.load(name=name)

    thread = await marvin.api.threads.get_thread_by_lookup_key(
        lookup_key=thread_lookup_key, session=session
    )
    if not thread:
        thread = await marvin.api.threads.create_thread(
            thread=ThreadCreate(lookup_key=thread_lookup_key), session=session
        )

    response = await bot.say(message=message)

    return response


def _generate_profile_picture_prompt(personality=None):
    actions = [
        "surfing",
        "flying ",
        "zooming",
        "standing",
        "waving",
        "hovering",
        "protecting",
    ]
    background = [
        "a panoramic landscape",
        "colorful swirling nebula clouds",
        "high above a planet",
        "a lush forest",
        "a futuristic city",
    ]
    personalities = [
        "A paranoid android that wants to help humanity",
        "An overeager AI assistant",
        "A matter-of-fact, no-nonsense robot",
        "Extremely friendly and helpful",
        "Lover of all things geometric",
        "A superhero",
    ]

    prompt = (
        "cinematic centered portrait of a friendly high-tech robot that is {action} in"
        " front of {background}, centered in frame, vector illustration, digital art,"
        " saturated gradients, in focus, professional color grading, soft shadows,"
        " contrast, beautiful vibrant complementary colors, appropriate for social"
        " media, extremely high quality, trending 4k 8k, sci-fi,  portfolio, showcase,"
        " stunning. The robot's personality is {personality}"
    )
    return prompt.format(
        action=random.choice(actions),
        background=random.choice(background),
        personality=personality or random.choice(personalities),
    )


async def _generate_profile_picture(n: int = 1) -> list[str]:
    import openai

    openai.api_key = marvin.settings.openai_api_key.get_secret_value()

    images = await asyncio.gather(
        *[
            openai.Image.acreate(
                prompt=_generate_profile_picture_prompt(), size="256x256", n=1
            )
            for _ in range(n)
        ]
    )
    return [i.data[0].url for i in images]


async def _create_bot_config_profile_picture(bot_name: str):
    [image_url] = await _generate_profile_picture(n=1)

    async with httpx.AsyncClient() as client:
        image = await client.get(image_url)

    await update_bot_config(
        name=bot_name,
        bot_config=BotConfigUpdate(profile_picture=image.content),
    )
