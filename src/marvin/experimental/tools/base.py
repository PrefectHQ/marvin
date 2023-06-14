from pydantic import Field, validator

from marvin.utilities.types import MarvinBaseModel, function_to_schema

SENTINEL = "__SENTINEL__"


class Tool(MarvinBaseModel):
    name: str = None
    description: str = None
    is_final_tool: bool = Field(
        False,
        description="This tool's response should be returned directly to the user",
    )

    @validator("name", always=True)
    def default_name_from_class_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    def run(self):
        raise NotImplementedError()

    def as_function_schema(self) -> dict:
        schema = function_to_schema(self.run)
        schema.pop("title", None)
        return dict(
            name=self.name,
            description=self.description or "",
            parameters=schema,
        )
