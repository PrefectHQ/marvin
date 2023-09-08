from typing import TypeVar

from fastapi._compat import PYDANTIC_V2, _model_dump  # type: ignore[import-private]
from pydantic import BaseModel

_ModelT = TypeVar("_ModelT", bound=BaseModel)

try:
    from pydantic import SecretStr
    from pydantic.v1 import Field as V1Field
    from pydantic.v1 import root_validator, validator
    from pydantic_settings import BaseSettings

except ImportError:
    from pydantic import BaseSettings, SecretStr, root_validator, validator
    from pydantic import Field as V1Field


def model_copy(model: _ModelT) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_copy()  # type: ignore
    return model.copy()  # type: ignore


__all__ = [
    "BaseSettings",
    "SecretStr",
    "V1Field",
    "model_copy",
    "_model_dump",
    "root_validator",
    "validator",
]
