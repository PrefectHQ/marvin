import sys
from types import GenericAlias
from typing import Any, Callable, Literal, Union

from pydantic import BaseModel

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec  # noqa
else:
    from typing import ParamSpec  # noqa


# Type aliases.
# They are here for future use:
# As of writing, VS Code imports aren't displaying correctly, so these are
# currently unused. They are here for future use.
# TODO: Fix this.

FUNCTION = Union[Callable[..., Any], type[BaseModel], dict[str, Any]]
RESPONSE_MODEL = Union[type, GenericAlias, type[BaseModel], Callable[..., Any]]
FUNCTION_CALL = Union[Literal["auto"], dict[Literal["name"], str], None]
