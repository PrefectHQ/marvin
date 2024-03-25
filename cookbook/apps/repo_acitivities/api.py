import typing

import marvin
import uvicorn
from config import settings
from fastapi import FastAPI, Request
from gh_util.types import GitHubWebhookRequest
from handlers import handle_repo_request
from pydantic_core import from_json


def save_request(request: GitHubWebhookRequest):
    if not (path := settings.home / request.event.repository.name).exists():
        path.mkdir()

    event_log_path = (
        path
        / f"{request.event.action}_{request.headers.event}_{request.headers.delivery}.json"
    )
    event_log_path.write_text(request.model_dump_json(indent=2))


class FasterRequest(Request):
    async def json(self) -> typing.Any:
        if not hasattr(self, "_json"):
            self._json = from_json(await self.body())
        return self._json


@marvin.fn(model_kwargs={"model": "gpt-3.5-turbo", "temperature": 1.2})
def say_you_are_healthy(in_the_style_of: str = "Top Boy (UK tv show)") -> str:
    """give an extremely short message that you are healthy `in_the_style_of`
    a given person or character.

    For example, if `in_the_style_of` is "Hagrid (Harry Potter)",
    > "Bloody hell, I haven't felt this good since Dumbledore gave me a dragon egg!"
    """


app = FastAPI()


@app.get("/")
def healthcheck() -> str:
    return say_you_are_healthy()


@app.post("/webhook")
async def repo_event(request: FasterRequest):
    req = GitHubWebhookRequest(
        headers=dict(request.headers), event=await request.json()
    )

    if settings.test_mode:
        save_request(req)

    await handle_repo_request.submit(req)

    return {"message": "repo event received"}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000)
