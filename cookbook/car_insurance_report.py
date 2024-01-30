from enum import Enum

import marvin
from pydantic import BaseModel, Field


class Severity(str, Enum):
    minor = "minor"
    moderate = "moderate"
    severe = "severe"


class Damage(BaseModel):
    severity: Severity = Field(
        description="The severity of the damage.",
    )
    description: str = Field(
        description="A description of the damage.",
    )


class DamageReport(BaseModel):
    description: dict[str, Damage] = Field(
        default_factory=dict,
        description="Each key should be a distinct, damaged location on the vehicle.",
    )


image = marvin.beta.Image(
    path_or_url="https://cs.copart.com/v1/AUTH_svc.pdoc00001/lpp/0923/e367ca327c564c9ba8368359f456664f_ful.jpg"
)  # its a dented up car

report = marvin.beta.vision.extract(image, DamageReport)

print(report)
