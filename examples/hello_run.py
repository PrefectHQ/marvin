from typing import Annotated, TypedDict

from pydantic import Field

import marvin


class Location(TypedDict):
    name: str
    lat: Annotated[float, Field(ge=-90, le=90)]

print(
    marvin.run(
        "in which city is the university of michigan located?",
        result_type=Location,
    )
)
