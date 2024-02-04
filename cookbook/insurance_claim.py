"""Using AI vision to evaluate car damage and submit an insurance claim using Marvin
and Prefect interactive workflows.

authored by: @kevingrismore and @zzstoatzz
"""

from enum import Enum
from typing import TypeVar

import marvin
from prefect import flow, pause_flow_run
from prefect.input import RunInput
from pydantic import BaseModel, Field, create_model


class Severity(str, Enum):
    minor = "Minor"
    moderate = "Moderate"
    severe = "Severe"


M = TypeVar("M", bound=BaseModel)


class Damage(BaseModel):
    location: str = Field(
        description="The location of the damage on the car.",
    )
    severity: Severity = Field(
        description="The severity of the damage.",
    )
    description: str = Field(
        description="A description of the damage.",
    )


def build_damage_report_model(damages: list[Damage]) -> M:
    """TODO we should be able to have a static `DamageReport` model
     with a `list[Damage]` field but it would not yet be rendered nicely.
    """
    return create_model(
        "DamageReport",
        **{f"{damage.location}": (Damage, ...) for damage in damages},
        __base__=RunInput,
    )


@flow(log_prints=True)
async def interactive_damage_report(car_id: int = 1):
    image_url = get_car_image(car_id)
    damages = evaluate_damage(image_url)

    DamageReport = build_damage_report_model(damages)

    car = await pause_flow_run(
        wait_for_input=DamageReport.with_initial_data(
            description=(
                "Please audit the generated damage report based on the following image:"
                ""
                f"![image]({image_url})"
            ),
            **{damage.location: damage for damage in damages},
        )
    )

    submit_damage_report(car)


def evaluate_damage(image_url: str) -> list[Damage]:
    return marvin.beta.extract(
        data=marvin.beta.Image(image_url),
        target=Damage,
        instructions=(
            "A car crash occurred. Please BRIEFLY evaluate the damage ON THE CAR."
            " Only include the damage that is visible in the image - do not assume additional damage."
            " Be sure to include appropriate severity levels for each damage location."
        ),
    )[:2]  # Limit to two damages for the sake of the example.


def get_car_image(car_id: str):
    """hypothetical function to get a car image from a car id."""
    return "https://cs.copart.com/v1/AUTH_svc.pdoc00001/lpp/0923/e367ca327c564c9ba8368359f456664f_ful.jpg"


def submit_damage_report(report: M):
    """hypothetical function to submit a damage report."""
    print(f"Submitting damage report: {report}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(interactive_damage_report())
