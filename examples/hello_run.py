from typing import Annotated, TypedDict

from pydantic import Field

import marvin


class Location(TypedDict):
    name: str
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]


print(
    marvin.run(
        "in which city is the university of michigan located?",
        result_type=Location,
    )
)
