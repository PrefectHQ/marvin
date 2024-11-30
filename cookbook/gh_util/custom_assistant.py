# /// script
# dependencies = ["marvin", "gh-util"]
# ///

from gh_util.api import functions  # pip install gh-util
from marvin.beta.applications import Application
from pydantic import BaseModel, Field


class Memory(BaseModel):
    notes: list[str] = Field(default_factory=list)


octocat = Application(
    name="octocat",
    state=Memory(),
    tools=[f for f in functions if f.__name__ != "run_git_command"],
)

if __name__ == "__main__":
    # uv run cookbook/gh_util/custom_assistant.py
    octocat.chat("what's the latest release of prefecthq/marvin?")
