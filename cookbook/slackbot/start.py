from concurrent.futures import ThreadPoolExecutor
from typing import List

import controlflow as cf
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

# Initialize FastAPI app
app = FastAPI()
executor = ThreadPoolExecutor(max_workers=30)


class SlackEvent(BaseModel):
    type: str
    user: str
    text: str
    channel: str
    ts: str


class SlackChallenge(BaseModel):
    token: str
    challenge: str
    type: str


class Discovery(BaseModel):
    question: str = Field(description="the question the user is actually asking")
    prefect_version: str = Field(
        description="the version of Prefect the user is mentioning or using"
    )


class ExcerptSummary(BaseModel):
    executive_summary: str = Field(description="at most 3 sentences summary")
    sources: List[str] = Field(
        default_factory=list, description="sources cited in summary"
    )


async def search_knowledgebase(query: str) -> str:
    """Search knowledgebase for answer to user's question."""
    # This is a placeholder. In a real implementation, you'd integrate with your actual knowledge base.
    return f"Searched knowledge base for: {query}"


slackbot = cf.Agent(name="Slackbot", tools=[search_knowledgebase])


@cf.flow(agents=[slackbot])
def answer_slack_question(event: SlackEvent):
    """Answer user's Slack question."""
    discovery = cf.Task(
        "Discover and gather the user's question and Prefect version",
        user_access=True,
        result_type=Discovery,
        context={"event": event},
    )

    summary = cf.Task(
        "Get a summary of the answer from the knowledgebase",
        user_access=True,
        context=dict(discovery=discovery),
        result_type=ExcerptSummary,
    )

    return cf.Task(
        "Compose the answer to the user's question",
        context=dict(summary=summary),
    )


def handler(event: SlackEvent):
    response = answer_slack_question(event)
    print(response)


@app.post("/chat")
async def slack_events(request: Request):
    body = await request.json()

    if "challenge" in body:
        return SlackChallenge(**body)

    event = SlackEvent(**body["event"])

    if event.type == "message" and not event.text.startswith("Slackbot:"):
        executor.submit(handler, event)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4200)
