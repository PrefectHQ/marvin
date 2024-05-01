from enum import Enum

import logfire
import openai
from fastapi import Body, FastAPI
from marvin import fn
from marvin.client import AsyncMarvinClient
from pydantic import BaseModel

app = FastAPI()
client = openai.AsyncClient()

logfire.configure(pydantic_plugin=logfire.PydanticPlugin(record="all"))
logfire.instrument_openai(client)
logfire.instrument_fastapi(app)


class Seniority(Enum):
    """ranked seniority levels for candidates"""

    JUNIOR = 1
    MID = 2
    SENIOR = 3
    STAFF = 4


class Candidate(BaseModel):
    name: str
    self_identified_seniority: Seniority
    bio: str


class Role(BaseModel):
    title: str
    desired_seniority: Seniority
    description: str


@fn(client=AsyncMarvinClient(client=client))
def choose_among_candidates(cohort: list[Candidate], role: Role) -> Candidate:
    return (
        f"We need a {role.desired_seniority.name} (at least) {role.title} that can "
        f"most likely fulfill a job of this description:\n{role.description}\n"
    )


@logfire.instrument("Dystopian Interview Process", extract_args=True)
def dystopian_interview_process(candidates: list[Candidate], role: Role) -> Candidate:
    senior_enough_candidates = [
        candidate
        for candidate in candidates
        if candidate.self_identified_seniority.value >= role.desired_seniority.value
    ]
    logfire.info(
        "Candidates at or above {seniority} level: {cohort}",
        cohort=[c.name for c in senior_enough_candidates],
        seniority=role.desired_seniority,
    )
    if len(senior_enough_candidates) == 1:
        return senior_enough_candidates[0]

    with logfire.span("Choosing among candidates"):
        return choose_among_candidates(senior_enough_candidates, role)


@app.post("/interview")
async def interview(
    candidates: list[Candidate] = Body(..., description="List of candidates"),
    role: Role = Body(..., description="Role to fill"),
) -> Candidate:
    best_candidate = dystopian_interview_process(candidates, role)
    logfire.info("Best candidate: {best_candidate}", best_candidate=best_candidate)
    return best_candidate


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
