import json

from prefect import flow, task
from prefect.blocks.system import JSON
from prefect.events import Event
from prefect.exceptions import ObjectNotFound

TOKEN_TRACKER_BLOCK_NAME = "marvin-bot-token-usage"


@task
async def increment_token_tracker(event: Event, token_tracker_block_name: str) -> int:
    try:
        token_tracker = await JSON.load(token_tracker_block_name)
    except ValueError as exc:
        if isinstance(exc.__cause__, ObjectNotFound):
            token_tracker = JSON(
                value={
                    "total_tokens": 0,
                },
            )
            await token_tracker.save(token_tracker_block_name)
        else:
            raise

    token_tracker.value["total_tokens"] += (
        total_tokens := event.payload["total_tokens"]
    )

    await token_tracker.save(token_tracker_block_name, overwrite=True)

    return total_tokens


@flow(
    name="Increment Token Usage on Bot Mention",
    log_prints=True,
)
async def increment_token_usage(
    event_str: str,
    token_tracker_block_name: str = TOKEN_TRACKER_BLOCK_NAME,
):
    event_dict = json.loads(event_str)

    n_tokens_used = await increment_token_tracker(
        event=Event(**event_dict),
        token_tracker_block_name=token_tracker_block_name,
    )
    print(f"Marvin used {n_tokens_used} tokens in this event.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(increment_token_usage("""
    {
        "event": "test",
        "resource": {"prefect.resource.id": "marvin-bot-test"},
        "payload": {"total_tokens": 10}
    }
    """))
