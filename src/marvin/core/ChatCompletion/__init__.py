from marvin.pydantic import validate_arguments, BaseModel
from typing import Literal
from marvin.utilities.module_loading import import_string


class Model(BaseModel):
    model: str
    path: str

    def module(self):
        return import_string(f"{self.path}.ChatCompletion")

    def chat_completion(self, **kwargs):
        return self.module()(_defaults={**self.dict(), **kwargs})

    def dict(self, **kwargs):
        return super().dict(**kwargs, exclude={"path"})


models = [
    Model(model="gpt-3.5-turbo", path="marvin.core.ChatCompletion.providers.openai"),
    Model(model="gpt-4", path="marvin.core.ChatCompletion.providers.openai"),
    Model(model="claude-1", path="marvin.core.ChatCompletion.providers.anthropic"),
    Model(model="claude-2", path="marvin.core.ChatCompletion.providers.anthropic"),
]

registry = {model.model: model for model in models}


@validate_arguments
def ChatCompletion(
    model: Literal[
        "gpt-3.5-turbo",
        "gpt-4",
        "claude-1",
        "claude-2",
    ],
    **kwargs,
):
    model = registry[model]
    return model.chat_completion(**kwargs)
