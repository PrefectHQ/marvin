from typing import Annotated, Literal, TypedDict

from pydantic import Field

import marvin
from marvin.fns.cast import DEFAULT_PROMPT


class Tornado(TypedDict):
    enhanced_fujita_scale: Literal[1, 2, 3, 4, 5]
    fatalities: int
    description: Annotated[str, Field(description="A short story about the tornado")]


if __name__ == "__main__":
    marvin.cast(
        "Joplin EF5",
        Tornado,
        prompt=(
            DEFAULT_PROMPT
            + "\n\n You're a history nerd who compares all new things to old things."
        ),
    )
