"""Base models for Marvin."""

from pydantic import BaseModel, ConfigDict


class MarvinModel(BaseModel):
    """Pydantic base model that forbids extra fields and validates assignments."""

    model_config = ConfigDict(
        extra="forbid",  # no extra fields allowed
        frozen=False,  # allow mutation
        validate_assignment=True,  # validate on attribute assignment
        validate_default=True,  # validate default values
    )
