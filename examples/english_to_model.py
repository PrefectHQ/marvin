from typing import Annotated, Any, TypedDict

from pydantic import Field, create_model

import marvin


class FieldDefinition(TypedDict):
    type: Annotated[
        str,
        Field(
            description="string that can be eval()'d into a Python type",
            examples=["str", "int", "list[str]", "dict[str, int]", "tuple[str, int]"],
        ),
    ]
    description: str
    properties: dict[str, Any]


class CreateModelInput(TypedDict):
    model_name: str
    fields: dict[str, FieldDefinition]
    description: str


create_model_input = marvin.cast(
    "a Movie with a title, release year, and a list of actors",
    target=CreateModelInput,
    instructions="suitable inputs for pydantic.create_model for the described schema",
)

Movie = create_model(
    create_model_input["model_name"],
    __doc__=create_model_input["description"],
    __config__=None,
    __module__=__name__,
    __validators__=None,
    __cls_kwargs__=None,
    **{
        k: (eval(v["type"]), Field(description=v["description"]))
        for k, v in create_model_input["fields"].items()
    },
)
print(marvin.cast("red or blue pill", target=Movie).model_dump_json(indent=2))
