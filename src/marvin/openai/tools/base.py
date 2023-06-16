from functools import partial
from typing import Callable, Optional

from pydantic import Field, validator

from marvin.utilities.types import MarvinBaseModel, function_to_schema

SENTINEL = "__SENTINEL__"


class Tool(MarvinBaseModel):
    name: str = None
    description: str = None
    fn: Optional[Callable] = None
    is_final: bool = Field(
        False,
        description="This tool's response should be returned directly to the user",
    )

    @classmethod
    def from_function(cls, fn, is_final=False):
        # assuming fn has a name and a description
        name = fn.__name__
        description = fn.__doc__
        return cls(name=name, description=description, fn=fn, is_final=is_final)

    @validator("name", always=True)
    def default_name_from_class_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    def run(self, *args, **kwargs):
        if not self.fn:
            raise NotImplementedError()
        else:
            return self.fn(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def as_function_schema(self) -> dict:
        schema = function_to_schema(self.fn or self.run)
        schema.pop("title", None)
        return dict(
            name=self.name,
            description=self.description or "",
            parameters=schema,
        )


def tool(arg=None, *, is_final=False):
    if callable(arg):  # Direct function decoration
        return Tool.from_function(arg, is_final=is_final)
    elif arg is None:  # Partial application
        return partial(tool, is_final=is_final)
    else:
        raise TypeError("Invalid argument passed to decorator.")
