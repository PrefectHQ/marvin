import typing

import marvin
import uvicorn
from config import settings
from devtools import debug
from fastapi import FastAPI, Request
from gh_util.types import GitHubWebhookEvent
from pydantic import BaseModel, Field
from pydantic_core import from_json


class GitHubWebhookEventHeaders(BaseModel):
    model_config = dict(extra="ignore")

    host: str = Field(...)
    event: str = Field(alias="x-github-event")
    hook_id: int = Field(alias="x-github-hook-id")
    delivery: str = Field(alias="x-github-delivery")


class GitHubWebhookRequest(BaseModel):
    headers: GitHubWebhookEventHeaders
    event: GitHubWebhookEvent


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
        if not (path := settings.home / req.event.repository.name).exists():
            path.mkdir()
        (
            path / f"{req.event.action}_{req.headers.event}_{req.headers.delivery}.json"
        ).write_text(req.model_dump_json(indent=2))
    debug(req.event)

    match req.event.repository.get("full_name"):
        case "zzstoatzz/gh":
            # do something
            pass
        case "prefecthq/marvin":
            # do something
            pass
        case _:
            # do nothing
            pass

    return {"message": "repo event received"}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
