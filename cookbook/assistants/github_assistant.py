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

# $ marvin assistant register cookbook/assistants/github_assistant.py:octocat

# > what's the latest release of prefecthq/marvin?

# see https://github.com/PrefectHQ/marvin/pull/875
