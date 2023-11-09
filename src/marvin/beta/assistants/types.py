from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

import marvin.utilities.pydantic


class Function(BaseModel):
    name: str
    description: Optional[str]
    parameters: dict
    fn: Callable = Field(exclude=True)

    @classmethod
    def from_function(cls, fn: Callable):
        model = marvin.utilities.pydantic.cast_callable_to_model(fn)
        return cls(
            name=fn.__name__,
            description=fn.__doc__,
            parameters=model.schema()["properties"],
            fn=fn,
        )


class Tool(BaseModel):
    type: str
    function: Optional[Function]

    @classmethod
    def from_function(cls, fn: Callable):
        return cls(type="function", function=Function.from_function(fn))


class Message(BaseModel):
    id: str
    thread_id: str
    content: list[dict[str, Any]]
    created_at: int
    role: str
    assistant_id: Optional[str] = None
    run_id: Optional[str] = None
    file_ids: list[str] = []
    metadata: dict = {}


class Run(BaseModel):
    id: str
    thread_id: str
    created_at: int
    status: str
    model: str
    instructions: Optional[str]
    tools: list[dict[str, Any]]
    metadata: dict[str, str]
