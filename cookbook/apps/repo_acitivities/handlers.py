from typing import Any

from devtools import debug
from gh_util.types import GitHubWebhookRequest
from marvin.utilities.redis import get_async_redis_client
from prefect import task
from prefect.task_server import serve
from pydantic import BaseModel


# default handler
async def _default_handler(request: GitHubWebhookRequest) -> GitHubWebhookRequest:
    debug(request)
    print(f"got {request.headers.event} event for {request.event.repository.full_name}")
    return request


# handlers for specific repositories
HANDLERS = {
    "zzstoatzz/gh": _default_handler,
    "prefecthq/marvin": _default_handler,
    # add more handlers for specific repositories here
}


# repo event handler task
@task(
    log_prints=True,
    task_run_name="Handle {request.headers.event} event for {request.event.repository.full_name}",
)
async def handle_repo_request(request: GitHubWebhookRequest) -> Any:
    full_repo_name = request.event.repository.full_name
    request_handler = HANDLERS.get(full_repo_name, _default_handler)
    handler_result = await request_handler(request)
    if isinstance(handler_result, BaseModel) and (
        serialized_result := handler_result.model_dump_json()
    ):
        redis = await get_async_redis_client()
        request_key = (
            f"{full_repo_name}:{request.headers.event}:{request.headers.delivery}"
        )
        await redis.set(request_key, serialized_result)
        print(f"serialized & saved to redis @ {request_key}")


# serve the main task
if __name__ == "__main__":
    serve(handle_repo_request)
