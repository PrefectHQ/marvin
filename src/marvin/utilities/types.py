import inspect
import logging
from typing import Any, Callable

import pydantic
from pydantic import BaseModel, PrivateAttr

from marvin.utilities.logging import get_logger


class LoggerMixin(BaseModel):
    """
    BaseModel mixin that adds a private `logger` attribute
    """

    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = get_logger(type(self).__name__)

    @property
    def logger(self):
        return self._logger


def function_to_schema(function: Callable[..., Any], name: str = None) -> dict:
    """
    Converts a function's arguments into an OpenAPI schema by parsing it into a
    Pydantic model. To work, all arguments must have valid type annotations.
    """
    signature = inspect.signature(function)

    fields = {
        p: (
            signature.parameters[p].annotation,
            (
                signature.parameters[p].default
                if signature.parameters[p].default != inspect._empty
                else ...
            ),
        )
        for p in signature.parameters
        if p != getattr(function, "__self__", None)
    }

    # Create Pydantic model
    try:
        Model = pydantic.create_model(name or function.__name__, **fields)
    except RuntimeError as exc:
        if "see `arbitrary_types_allowed` " in str(exc):
            raise ValueError(
                f"Error while inspecting {function.__name__} with signature"
                f" {signature}: {exc}"
            )
        else:
            raise

    return Model.schema()
