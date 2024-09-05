# /// script
# dependencies = [
#   "marvin",
#   "prefect",
#   "gh-util"
# ]

from typing import Annotated

import marvin
from gh_util.types import GitHubWebhookEvent
from prefect import flow, task
from prefect.events import DeploymentEventTrigger
from prefect.variables import Variable
from pydantic import Field

MAX_QUEUE_SIZE = 5


trigger = DeploymentEventTrigger(  # type: ignore
    expect={"prefecthq/prefect*"},
    parameters={
        "event": {
            "__prefect_kind": "json",
            "value": {
                "__prefect_kind": "jinja",
                "template": "{{ event.payload | tojson }}",
            },
        }
    },
)


@task
def summarize_and_speak(summaries: list[str]):
    """
    Summarize all event summaries in the queue and speak the final summary
    """
    joined_summaries = "\n".join(summaries)
    final_summary = marvin.cast(
        joined_summaries,
        target=Annotated[  # type: ignore
            str, Field(description="A concise summary of the last 5 events")
        ],
    )
    audio = marvin.speak(final_summary)
    audio.play()


@flow(log_prints=True)
def process_event(event: GitHubWebhookEvent):
    """Process a single event, summarize it, and add to the queue"""
    summary = marvin.cast(
        event.model_dump_json(exclude_none=True),
        target=Annotated[  # type: ignore
            str, Field(description="A brief summary of this single event")
        ],
    )

    summaries: list[str] | None = Variable.get("event_summaries", default=None)  # type: ignore
    if summaries is None:
        summaries = []
    summaries.append(summary)
    Variable.set("event_summaries", summaries, overwrite=True)
    print(f"We've seen {len(summaries)} event(s)")

    if len(summaries) == MAX_QUEUE_SIZE:
        summarize_and_speak(summaries)
        Variable.set("event_summaries", [], overwrite=True)


if __name__ == "__main__":
    # uv run --no-project cookbook/flows/read_me_events.py
    process_event.serve(triggers=[trigger])
