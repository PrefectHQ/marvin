import inspect
from datetime import datetime
from typing import Any, Union
from zoneinfo import ZoneInfo

import pydantic
from jinja2 import Environment as BaseEnvironment
from jinja2 import StrictUndefined, select_autoescape
from jinja2 import Template as BaseTemplate


class Environment(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    environment: BaseEnvironment = pydantic.Field(
        default=BaseEnvironment(
            autoescape=select_autoescape(default_for_string=False),
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=True,
            undefined=StrictUndefined,
        )
    )

    globals: dict[str, Any] = pydantic.Field(
        default_factory=lambda: {
            "now": lambda: datetime.now(ZoneInfo("UTC")),
            "inspect": inspect,
        }
    )

    @pydantic.model_validator(mode="after")
    def setup_globals(self) -> "Environment":
        self.environment.globals.update(self.globals)  # type: ignore
        return self

    def render(self, template: Union[str, BaseTemplate], **kwargs: Any) -> str:
        if isinstance(template, str):
            return self.environment.from_string(template).render(**kwargs)
        return template.render(**kwargs)
