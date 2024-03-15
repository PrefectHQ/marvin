from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode

from marvin.types import Function, FunctionTool, ToolSet


class FunctionSchema(GenerateJsonSchema):
    def generate(self, schema: Any, mode: JsonSchemaMode = "validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema.pop("title", None)
        return json_schema


def cast_model_to_tool(
    model: type[BaseModel],
) -> FunctionTool[BaseModel]:
    model_name = model.__name__
    model_description = model.__doc__
    return FunctionTool[BaseModel](
        type="function",
        function=Function[BaseModel](
            name=model_name,
            description=model_description,
            model=model,
            parameters=model.model_json_schema(schema_generator=FunctionSchema),
        ),
    )


def cast_model_to_toolset(
    model: type[BaseModel],
) -> ToolSet[BaseModel]:
    tools = [cast_model_to_tool(model)]
    name = getattr(tools[0].function, "name", None)
    if name is None:
        raise ValueError("Tool name is required")
    return ToolSet[BaseModel](
        tools=tools, tool_choice={"type": "function", "function": {"name": name}}
    )
