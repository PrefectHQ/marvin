""" Uses the JSON block to track the total number of tokens used by a slackbot.

In `src/marvin/server/slackbot.py`, we use `prefect.events.emit_event` to send a payload to
Prefect Cloud when the bot is mentioned and a response is sent. We configure an automation
in Prefect Cloud to jinja template the payload as parameters to a run of this flow.
"""  # noqa: E501
import pendulum
from prefect import flow, task
from prefect.blocks.notifications import SlackWebhook
from prefect.blocks.system import JSON
from prefect.exceptions import ObjectNotFound

TOKEN_TRACKER_BLOCK_NAME = "marvin-bot-token-usage"
GLOBAL_TOKEN_LIMIT = int(1e5)


@task
async def increment_token_tracker(
    total_tokens: int, token_tracker_block_name: str
) -> JSON:
    try:
        token_tracker = await JSON.load(token_tracker_block_name)
    except ValueError as exc:
        if isinstance(exc.__cause__, ObjectNotFound):
            token_tracker = JSON(
                value={
                    "total_tokens": 0,
                    "global_token_limit": GLOBAL_TOKEN_LIMIT,
                    "updated_at": pendulum.now().isoformat(),
                },
            )
        else:
            raise

    token_tracker.value["total_tokens"] += total_tokens

    if token_tracker.value["total_tokens"] > token_tracker.value["global_token_limit"]:
        slack_pager = await SlackWebhook.load("marvin-bot-pager")
        await slack_pager.notify(
            "Marvin's LLM usage has exceeded"
            f" {token_tracker.value['global_token_limit']=!r}."
        )

    return token_tracker


@task
async def summarize_weekly_token_usage(token_tracker: JSON) -> JSON:
    slack_pager = await SlackWebhook.load("marvin-bot-pager")

    message = f"Marvin used {token_tracker.value['total_tokens']} tokens this week."

    print(message)
    slack_pager.notify(message)

    token_tracker.value.update(
        {
            "total_tokens": 0,
            "updated_at": pendulum.now().isoformat(),
        }
    )

    return token_tracker


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

    token_tracker = await increment_token_tracker(
        total_tokens=event_total_tokens,
        token_tracker_block_name=token_tracker_block_name,
    )
    print(f"Marvin used {event_total_tokens} tokens in this event.")

    # If it's been more than a week since we last updating token usage, then
    # summarize the weekly token usage and reset the token tracker.
    if pendulum.parse(token_tracker.value["updated_at"]) < pendulum.now().subtract(
        weeks=1
    ):
        token_tracker = await summarize_weekly_token_usage(token_tracker=token_tracker)

    await token_tracker.save(token_tracker_block_name, overwrite=True)


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        increment_token_usage(
            user_question="What is the weather like today?",
            bot_response="It's sunny and 75 degrees.",
            total_tokens_str="20",
            token_tracker_block_name="test-token-tracker",
        )
    )
