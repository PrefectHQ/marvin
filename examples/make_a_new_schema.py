"""
Dynamically create a new schema and make instances of it
"""

from typing import Literal, NotRequired, TypedDict

from prefect import task
from prefect.cache_policies import INPUTS
from pydantic import BaseModel, TypeAdapter, ValidationError

import marvin
from marvin.utilities.jsonschema import jsonschema_to_type


class SomeSubclass(BaseModel): ...


class Field(TypedDict):
    type: str
    required: bool
    minimum: NotRequired[int]
    maximum: NotRequired[int]
    enum: NotRequired[list[str]]


class Schema(TypedDict):
    type: Literal["object"]
    properties: dict[str, Field]
    required: list[str]


@task(cache_policy=INPUTS)
def make_schema(description: str) -> Schema:
    return marvin.cast(description, target=Schema)


Person = jsonschema_to_type(
    schema=make_schema("a person w a name, age, gender (male|female|non-binary)"),
    name="Person",
)


valid_person = TypeAdapter(SomeSubclass).validate_json(
    '{"name": "Sid Phillips", "age": 13, "gender": "male"}'
)

assert type(valid_person) is SomeSubclass, f"Expected Person, got {type(valid_person)}"
print(valid_person)

input_json = '{"name": "Mr Potatohead", "age": 3, "gender": "potato"}'
print(f"\n\n====trying input: {input_json}====\n\n")
try:
    TypeAdapter(Person).validate_json(input_json)
except ValidationError as e:
    print(e)
