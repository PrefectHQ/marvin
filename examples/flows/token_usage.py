from prefect import flow, task
from prefect.blocks.system import JSON
from prefect.exceptions import ObjectNotFound

TOKEN_TRACKER_BLOCK_NAME = "marvin-bot-token-usage"


@task
async def increment_token_tracker(total_tokens: int, token_tracker_block_name: str):
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

    token_tracker.value["total_tokens"] += total_tokens

    await token_tracker.save(token_tracker_block_name, overwrite=True)


@flow(
    name="Increment Token Usage on Bot Mention",
    log_prints=True,
)
async def increment_token_usage(
    user_question: str,
    bot_response: str,
    total_tokens_str: str,
    token_tracker_block_name: str = TOKEN_TRACKER_BLOCK_NAME,
):
    print(f"User question:\n{user_question}")

    print(f"Bot response:\n{bot_response}")

    event_total_tokens = int(total_tokens_str)

    await increment_token_tracker(
        total_tokens=event_total_tokens,
        token_tracker_block_name=token_tracker_block_name,
    )
    print(f"Marvin used {event_total_tokens} tokens in this event.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(increment_token_usage("""
    {
        "event": "test",
        "resource": {"prefect.resource.id": "marvin-bot-test"},
        "payload": {"total_tokens": 10}
    }
    """))
