from typing import Callable, Optional

from openai.types.beta.threads import ThreadMessage as OpenAIMessage
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.runs import RunStep as OpenAIRunStep
from pydantic import BaseModel, Field

import marvin.utilities.pydantic


class Function(BaseModel):
    name: str
    description: Optional[str]
    parameters: dict
    fn: Callable = Field(exclude=True)

    @classmethod
    def from_function(cls, fn: Callable, name: str = None, description: str = None):
        model = marvin.utilities.pydantic.cast_callable_to_model(fn)
        return cls(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            parameters=model.schema(),
            fn=fn,
        )


class Tool(BaseModel):
    type: str
    function: Optional[Function]

    @classmethod
    def from_function(cls, fn: Callable, name: str = None, description: str = None):
        return cls(
            type="function",
            function=Function.from_function(fn=fn, name=name, description=description),
        )


class RunResponse(BaseModel):
    run: OpenAIRun
    run_steps: list[OpenAIRunStep]
    messages: list[OpenAIMessage]
