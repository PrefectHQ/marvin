from typing import Any, Callable

import pydantic_ai

from marvin.utilities.types import AutoDataClass


class Actor(AutoDataClass):
    _dataclass_config = {"kw_only": True}

    def get_agentlet(
        self,
        result_types: list[type],
        tools: list[Callable[..., Any]] | None = None,
    ) -> pydantic_ai.Agent[Any, Any]:
        raise NotImplementedError("Subclass must implement get_agent")
