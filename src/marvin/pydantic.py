from pydantic.version import VERSION as PYDANTIC_VERSION
from pydantic_settings import BaseSettings

PYDANTIC_V2 = PYDANTIC_VERSION.startswith("2.")

if not PYDANTIC_V2:
    from pydantic import (
        BaseModel,
        Extra,
        Field,
        PrivateAttr,
        SecretStr,
        validate_arguments)
    from pydantic.main import ModelMetaclass

    ModelMetaclass = ModelMetaclass
    BaseModel = BaseModel
    BaseSettings = BaseSettings
    Field = Field
    SecretStr = SecretStr
    Extra = Extra
    PrivateAttr = PrivateAttr
    validate_arguments = validate_arguments
