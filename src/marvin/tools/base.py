import inspect
from functools import partial
from typing import Callable, Optional

from pydantic import BaseModel, validator

from marvin.engine.language_models import OpenAIFunction
from marvin.utilities.strings import jinja_env
from marvin.utilities.types import LoggerMixin, function_to_schema


class Tool(LoggerMixin, BaseModel):
    name: str = None
    description: str = None
    fn: Optional[Callable] = None

    @classmethod
    def from_function(cls, fn, name: str = None, description: str = None):
        # assuming fn has a name and a description
        name = name or fn.__name__
        description = description or fn.__doc__
        return cls(name=name, description=description, fn=fn)

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

    def argument_schema(self) -> dict:
        schema = function_to_schema(self.fn or self.run)
        schema.pop("title", None)
        return schema

    def as_openai_function(self) -> OpenAIFunction:
        schema = self.argument_schema()
        description = jinja_env.from_string(inspect.cleandoc(self.description or ""))
        description = description.render(**self.dict(), TOOL=self)

        return OpenAIFunction(
            name=self.name,
            description=description,
            parameters=schema,
            fn=self.run,
        )


def tool(arg=None, *, name: str = None, description: str = None):
    if callable(arg):  # Direct function decoration
        return Tool.from_function(arg, name=name, description=description)
    elif arg is None:  # Partial application
        return partial(tool, name=name, description=description)
    else:
        raise TypeError("Invalid argument passed to decorator.")
