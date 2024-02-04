"""Using AI vision to evaluate car damage and submit an insurance claim using Marvin
and Prefect interactive workflows.

authored by: @kevingrismore and @zzstoatzz
"""

from enum import Enum
from typing import TypeVar

import marvin
from prefect import flow, pause_flow_run
from prefect.artifacts import create_markdown_artifact
from prefect.input import RunInput
from pydantic import BaseModel, Field, create_model


class Severity(str, Enum):
    minor = "Minor"
    moderate = "Moderate"
    severe = "Severe"


M = TypeVar("M", bound=RunInput)


class DamagedPart(BaseModel):
    part: str = Field(
        description="short unique name for a damaged part",
        example="front_left_bumper",
    )
    severity: Severity = Field(
        description="severity of part damage",
    )
    description: str = Field(
        description="specific, but high level summary of damage in 1 sentence",
    )


def build_damage_report_model(damages: list[DamagedPart]) -> M:
    """TODO we should be able to have a static `DamageReportInput` model with
    a `list[DamagedPart]` field but it won't be rendered nice yet.
    """
    return create_model(
        "DamageReportInput",
        **{f"{damage.part}": (DamagedPart, ...) for damage in damages},
        __base__=RunInput,
    )


@flow(log_prints=True)
async def interactive_damage_report(image_url: str):
    damages = marvin_evaluate_damage(image_url)

    DamageReportInput = build_damage_report_model(damages)

    damage_report = await pause_flow_run(
        wait_for_input=DamageReportInput.with_initial_data(
            description=(
                "Please audit the damage report drafted from the submitted image:"
                f"\n![image]({image_url})"
            ),
            **{damage.part: damage for damage in damages},
        )
    )

    await submit_damage_report(damage_report, image_url)


def marvin_evaluate_damage(image_url: str) -> list[DamagedPart]:
    return marvin.beta.extract(
        data=marvin.beta.Image(image_url),
        target=DamagedPart,
        instructions=(
            "Give extremely brief, high-level descriptions of the damage."
            " Only include the 2 most significant damages, which may also be minor and/or moderate."
            # only want 2 damages for purposes of this example
        ),
    )


async def submit_damage_report(report: M, image_url: str):
    """hypothetical function to submit a damage report."""
    print(f"Submitting damage report: {report}")

    await create_markdown_artifact(
        markdown=(
            f"![image]({image_url})" "\n\n" f"**Damage Report:**\n\n" f"{report}"
        ),
    )


if __name__ == "__main__":
    import asyncio

    # or wherever you'd get your image from
    image_url = "https://cs.copart.com/v1/AUTH_svc.pdoc00001/lpp/0923/e367ca327c564c9ba8368359f456664f_ful.jpg"
    asyncio.run(interactive_damage_report(image_url))
