import asyncio
from typing import Callable, TypeVar

from ai import describe_event_as_key
from gh_util.logging import get_logger
from gh_util.types import (
    GitHubWebhookEvent,
    GitHubWebhookRequest,
)
from handlers import (
    DEFAULT_EVENT_HANDLERS,
    REPO_EVENT_HANDLERS,
    default_handler,
)
from marvin.utilities.redis import get_async_redis_client
from prefect import task
from prefect.task_server import serve
from pydantic import BaseModel

MAX_EVENTS = 100
TTL = 86400  # 1 day in seconds

logger = get_logger("handlers")

M = TypeVar("M", bound=BaseModel)


def dump_event(event: GitHubWebhookEvent) -> str:
    return event.model_dump_json(
        exclude={"sender", "repository", "performed_via_github_app"},
        exclude_none=True,
    )


# Repo event handler task
@task(
    log_prints=True,
    task_run_name="Handle {request.headers.event} event for {request.event.repository.full_name}",
)
async def handle_repo_request(
    request: GitHubWebhookRequest, handle_unknown_event: bool = False
):
    event_type = request.headers.event
    full_repo_name = request.event.repository.full_name

    repo_handlers = REPO_EVENT_HANDLERS.get(full_repo_name, DEFAULT_EVENT_HANDLERS)
    event_handler: Callable[..., M] | None = repo_handlers.get(event_type, None)

    if not event_handler:
        if handle_unknown_event:
            event_handler = default_handler
        else:
            print(f"Skipping handling of unknown event: {event_type}")
            return

    # process the event, generate a semantically interesting event key, save to redis
    results: tuple[M, str] = await asyncio.gather(
        event_handler(request),
        describe_event_as_key(event_digest=dump_event(request.event)),
    )

    handler_result, event_key_description = results

    repo_key = f"{full_repo_name}:events"
    event_key = f"{event_type}:{event_key_description}:{request.headers.delivery}"

    # Add the event to the repository's sorted set with the received_at timestamp as the score
    redis = await get_async_redis_client()
    await redis.zadd(repo_key, mapping={event_key: request._received_at.timestamp()})
    await redis.set(event_key, handler_result.model_dump_json(), ex=TTL)

    # Trim the repository's sorted set to maintain a maximum number of events
    await redis.zremrangebyrank(repo_key, 0, -MAX_EVENTS - 1)

    print(f"serialized event saved to redis: {repo_key} -> {event_key}")


# Serve the main handler task
if __name__ == "__main__":
    serve(handle_repo_request)
