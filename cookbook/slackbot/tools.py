from typing import Literal

import httpx

Topic = Literal["latest_prefect_version"]


async def get_latest_release_notes() -> str:
    """Gets the first whole h2 section from the Prefect RELEASE_NOTES.md file."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://raw.githubusercontent.com/PrefectHQ/prefect/main/RELEASE-NOTES.md"
        )
        return response.text.split("\n## ")[1]


tool_map = {"latest_prefect_version": get_latest_release_notes}


def get_info(topic: Topic) -> str:
    """A tool that returns information about a topic using
    one of many pre-existing helper functions. You need only
    provide the topic name, and the appropriate function will
    return information.

    As of now, the only topic is "latest_prefect_version".
    """

    try:
        return tool_map[topic]()
    except KeyError:
        raise ValueError(f"Invalid topic: {topic}")
